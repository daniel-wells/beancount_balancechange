""" Check balance assertion for CHANGE in balance
"""
__copyright__ = "Copyright (C) 2013-2016  Martin Blais, Daniel Wells 2022"
__license__ = "GNU GPLv2"

import collections
import re

from beancount.core.number import ONE
from beancount.core.number import ZERO
from beancount.core.data import Custom, Transaction
from beancount.core.data import Balance
from beancount.core import amount
from beancount.core import account
from beancount.core import realization
from beancount.core import getters

__plugins__ = ('balance_change',)


BalanceError = collections.namedtuple('BalanceError', 'source message entry')


def is_balance_change_entry(entry):
    return isinstance(entry, Custom) and entry.type == 'balance_change'

def get_expression_from_entry(entry):
    return entry.values[0].value

def get_expected_amount_from_entry(entry):
    return entry.values[1].value

def get_account_from_entry(entry):
    return re.match(
            '((Assets|Liabilities|Expenses|Equity|Income)(:\w+)+)',
            get_expression_from_entry(entry)).group(0)


def balance_change(entries, options_map):
    """Process the balance assertion directives.

    For each Balance directive, check that their expected balance corresponds to
    the actual balance computed at that time and replace failing ones by new
    ones with a flag that indicates failure.

    Args:
      entries: A list of directives.
      options_map: A dict of options, parsed from the input file.
    Returns:
      A pair of a list of directives and a list of balance check errors.
    """
    new_entries = []
    check_errors = []

    # This is similar to realization, but performed in a different order, and
    # where we only accumulate inventories for accounts that have balance
    # assertions in them (this saves on time). Here we process the entries one
    # by one along with the balance checks. We use a temporary realization in
    # order to hold the incremental tree of balances, so that we can easily get
    # the amounts of an account's subaccounts for making checks on parent
    # accounts.
    real_root = realization.RealAccount('')

    # Figure out the set of accounts for which we need to compute a running
    # inventory balance.
    balance_change_assertions = [entry
                                 for entry in entries
                                 if is_balance_change_entry(entry)]

    t1_dates = [entry.meta.get('since') for entry in balance_change_assertions]
    asserted_accounts = {get_account_from_entry(entry) for entry in balance_change_assertions}
    asserted_currencies = {get_expected_amount_from_entry(entry).currency for entry in balance_change_assertions}
    t1_amounts = {(bank,date,currency): "NaN" for bank,date,currency in zip(asserted_accounts, t1_dates, asserted_currencies)}

    # Add all children accounts of an asserted account to be calculated as well,
    # and pre-create these accounts, and only those (we're just being tight to
    # make sure).
    asserted_match_list = [account.parent_matcher(account_)
                           for account_ in asserted_accounts]
    for account_ in getters.get_accounts(entries):
        if (account_ in asserted_accounts or
            any(match(account_) for match in asserted_match_list)):
            realization.get_or_create(real_root, account_)

    # Get the Open directives for each account.
    open_close_map = getters.get_account_open_close(entries)

    def update_t1_amounts(entry, t1_amounts, real_root):
        entries_to_sum = [k for k,v in t1_amounts.items() if not isinstance(v, amount.Amount) and entry.date >= k[1]]
        for bal_check in entries_to_sum:
            # Sum up the current balances for this account and its
            # sub-accounts. We want to support checks for parent accounts
            # for the total sum of their subaccounts.
            real_account = realization.get(real_root, bal_check[0])
            assert real_account is not None, "Missing {}".format(bal_check[0])
            subtree_balance = realization.compute_balance(real_account, leaf_only=False)

            # Get only the amount in the desired currency.
            balance_amount = subtree_balance.get_currency_units(bal_check[2])
            t1_amounts[bal_check] = balance_amount


    for entry in entries:
        if isinstance(entry, Transaction):

            update_t1_amounts(entry, t1_amounts, real_root)

            # For each of the postings' accounts, update the balance inventory.
            for posting in entry.postings:
                real_account = realization.get(real_root, posting.account)

                # The account will have been created only if we're meant to track it.
                if real_account is not None:
                    # Note: Always allow negative lots for the purpose of balancing.
                    # This error should show up somewhere else than here.
                    real_account.balance.add_position(posting)

        elif is_balance_change_entry(entry):
            # Check that the currency of the balance check is one of the allowed
            # currencies for that account.
            expected_change = get_expected_amount_from_entry(entry)
            try:
                open, _ = open_close_map[get_account_from_entry(entry)]
            except KeyError:
                check_errors.append(
                    BalanceError(entry.meta,
                                 "Invalid reference to unknown account '{}'".format(
                                     get_account_from_entry(entry)), entry))
                continue

            if (expected_change is not None and
                open and open.currencies and
                expected_change.currency not in open.currencies):
                check_errors.append(
                    BalanceError(entry.meta,
                                 "Invalid currency '{}' for Balance directive: ".format(
                                     expected_change.currency),
                                 entry))

            # Sum up the current balances for this account and its
            # sub-accounts. We want to support checks for parent accounts
            # for the total sum of their subaccounts.
            real_account = realization.get(real_root, get_account_from_entry(entry))
            assert real_account is not None, "Missing {}".format(get_account_from_entry(entry))
            subtree_balance = realization.compute_balance(real_account, leaf_only=False)

            # Get only the amount in the desired currency.
            balance_amount = subtree_balance.get_currency_units(expected_change.currency)
            starting_amount = t1_amounts[(get_account_from_entry(entry),entry.meta['since'], get_expected_amount_from_entry(entry).currency)]

            # Check if the amount is within bounds of the expected amount.
            actual_change = amount.sub(balance_amount, starting_amount)
            diff_amount = amount.sub(actual_change, expected_change)
            entry.meta['starting_amount'] = starting_amount

            if abs(diff_amount.number) > 0.005:
                entry.meta['diff_amount'] = diff_amount
                check_errors.append(
                    BalanceError(entry.meta,
                                 ("Balance change check failed for '{}': "
                                  "expected a change of {} != actual change {} ({} {})").format(
                                      get_account_from_entry(entry), expected_change, actual_change,
                                      abs(diff_amount.number),
                                      ('too much'
                                       if diff_amount.number > 0
                                       else 'too little')),
                                 entry))

                # Substitute the entry by a failing entry, with the diff_amount
                # field set on it. I'm not entirely sure that this is the best
                # of ideas, maybe leaving the original check intact and insert a
                # new error entry might be more functional or easier to
                # understand.
                #entry = entry._replace(
                #    meta=entry.meta.copy(),
                #    diff_amount=diff_amount)

        new_entries.append(entry)

    return new_entries, check_errors
