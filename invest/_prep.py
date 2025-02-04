"""
Data prep tools for invest.
"""
from inspect import signature, Parameter

import yfinance as yf

_empty_parameter_value = Parameter.empty

_known_duplicate_pairs = (
    ('balance_sheet', 'balancesheet'),
    ('quarterly_balance_sheet', 'quarterly_balancesheet'),
    ('get_balance_sheet', 'get_balancesheet'),
    ('get_quarterly_balance_sheet', 'get_quarterly_balancesheet'),
)


def _remove_some_known_duplicates(s):
    for name, duplicate_name in _known_duplicate_pairs:
        if duplicate_name in s:
            s -= {duplicate_name}


def _method_has_defaults_for_all_arguments(func):
    parameters = signature(func).parameters
    if len(parameters) == 1:  # if only one param, it's the instance, so no arguments required, so...
        return True
    else:
        instance, first_real_param, *remaining_args = parameters.values()
        if first_real_param.default is not _empty_parameter_value:
            # if the first (real) param has a default, all other params must to (or be variable like *args or **kwargs)
            return True
        else:
            return False


_ticker_attrs_that_are_properties = {a for a in dir(yf.Ticker)
                                     if not a.startswith('_')
                                     and not callable(getattr(yf.Ticker, a))}

_ticker_attrs_that_are_callable = {a for a in dir(yf.Ticker)
                                   if not a.startswith('_')
                                   and callable(getattr(yf.Ticker, a))
                                   and _method_has_defaults_for_all_arguments}

_remove_some_known_duplicates(_ticker_attrs_that_are_properties)
_remove_some_known_duplicates(_ticker_attrs_that_are_callable)

# remove those callable attrs that start with "get_"

_getless_callable_attrs = {x[4:] for x in _ticker_attrs_that_are_callable if x.startswith('get_')}
_ticker_attrs_that_are_methods = (_getless_callable_attrs
                                  | {x for x in _ticker_attrs_that_are_callable if not x.startswith('get_')})
