__copyright__ = "Copyright (C) 2018  Martin Blais, Daniel Wells 2022"
__license__ = "GNU GPLv2"

import unittest

from beancount.parser import cmptest
from beancount import loader

from beancount_balancechange.balance_change import balance_change

class TestBalanceChange(cmptest.TestCase):

    @loader.load_doc(expect_errors=False)
    def test_balance_change_balanced(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 50 GBP
           Assets:BankA -50 GBP

        2020-01-07 custom "balance_change" Assets:BankA -50 GBP
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertEqual(len(errors), 0)

    @loader.load_doc(expect_errors=False)
    def test_balance_change_multi_txs(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 10 GBP
           Assets:BankA -10 GBP

        2020-01-06 txn "Example"
           Expenses:Food 40 GBP
           Assets:BankA -40 GBP

        2020-01-07 custom "balance_change" Assets:BankA -50 GBP
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertEqual(len(errors), 0)


    @loader.load_doc(expect_errors=False)
    def test_balance_change_balanced_with_subaccounts(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD
        2020-01-01 open Assets:BankA:Checking GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 50 GBP
           Assets:BankA:Checking -50 GBP

        2020-01-07 custom "balance_change" Assets:BankA -50 GBP
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertEqual(len(errors), 0)


    @loader.load_doc(expect_errors=False)
    def test_balance_change_unbalanced(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 50 GBP
           Assets:BankA -50 GBP

        2020-01-07 custom "balance_change" Assets:BankA -25GBP
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertEqual(len(errors), 1)


    @loader.load_doc(expect_errors=False)
    def test_balance_change_invalid_currency(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 50 GBP
           Assets:BankA -50 GBP

        2020-01-07 custom "balance_change" Assets:BankA -50 BTC
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertTrue("Invalid currency 'BTC'" in errors[0].message)
        self.assertEqual(len(errors), 2)


    @loader.load_doc(expect_errors=False)
    def test_balance_change_invalid_account(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA:Checking GBP, USD
        2020-01-01 open Expenses:Food GBP, USD

        2020-01-03 txn "Example"
           Assets:BankA:Checking 100 GBP
           Equity:Opening-Balances -100 GBP

        2020-01-05 txn "Example"
           Expenses:Food 50 GBP
           Assets:BankA:Checking -50 GBP

        2020-01-07 custom "balance_change" Assets:BankA -50 BTC
            since: 2020-01-04
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertTrue("Invalid reference to unknown account 'Assets:BankA'" in errors[0].message)
        self.assertEqual(len(errors), 1)

    @loader.load_doc(expect_errors=False)
    def test_balance_change_no_transactions_in_interval(self, entries, _, options_map):
        """
        2020-01-01 open Equity:Opening-Balances GBP, USD
        2020-01-01 open Assets:BankA GBP, USD

        2020-01-03 custom "balance_change" Assets:BankA 0 GBP
            since: 2020-01-02
        """
        new_entries, errors = balance_change(entries, options_map)
        self.assertEqual(len(errors), 0)


if __name__ == '__main__':
    unittest.main()
