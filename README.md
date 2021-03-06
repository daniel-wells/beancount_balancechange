![ci testing badge](https://github.com/daniel-wells/beancount_balancechange/actions/workflows/python-app.yml/badge.svg)

A [beancount](https://beancount.github.io/docs/) plugin that performs an assertion (check) on the change in balance between two dates.

For Income and Expense accounts the standard balance assertions aren't so useful
because we aren't interested in the absolute balance but rather the _change_ in balance.

This plugin allows you to assert that a balance has changed by a given amount between
two dates using the following syntax:
```
2021-04-06 custom "balance_change" Income:EmployerA -50000 GBP
    since: 2020-04-06
```
For example you might want to check your total income for the tax year matches that on your P60.

Installation:
```
pip install git+https://github.com/daniel-wells/beancount_balancechange.git
```

Usage:
Add the following line to your ledger file:
```
plugin "beancount_balancechange.balance_change"
```
