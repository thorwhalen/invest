from inspect import signature, Parameter
from importlib_resources import files
from functools import lru_cache
from typing import Iterable, Optional, Callable, Union
import os

import yfinance as yf
from py2store import KvReader, add_ipython_key_completions

data_files_posix_path = files('invest').joinpath('data')
DFLT_TICKER_SYMBOLS_FILENAME = 'default_ticker_symbols.csv'

_empty_parameter_value = Parameter.empty


def help_me_with(item: str):
    attr = getattr(yf.Ticker, item)
    print(f"{attr.__name__}\nwraps {attr}, whose signature is:\n{signature(attr)}\n{attr.__doc__}\n")


def _nice_kv_string(mapping):
    return ', '.join((f"{k}={v}" for k, v in mapping.items()))


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

_ticker_attrs_that_are_methods = {a for a in dir(yf.Ticker)
                                  if not a.startswith('_')
                                  and callable(getattr(yf.Ticker, a))
                                  and _method_has_defaults_for_all_arguments}


@lru_cache(maxsize=1)
def get_local_ticker_list():
    return {x for x in data_files_posix_path.joinpath(DFLT_TICKER_SYMBOLS_FILENAME).read_text().split('\n') if x}


# TODO: Use https://github.com/shilewenuw/get_all_tickers (or another) to get ticker symbol lists
# TODO: Use py2store explicit tools
@add_ipython_key_completions
class Tickers(KvReader):
    """
    A dict-like source of ticker symbols.
    Keys are ticker symbol strings and values are Ticker object (which offers a dict-like interface to more information)


    The first argument of Tickers is the ``ticker_symbols`` argument.

    One can specify a collection (``list``, ``set``, ``tuple``, etc.) of ticker symbol strings,
    or a path to a file containing a pickle of such a collection.

    The default is the string ``'local_list'`` which has the effect of using a default list
    (currently of about 4000 tickers), but it's contents can change in the future.

    Note that this ticker_symbols will have an effect on such affairs as
    ``list(tickers)``, ``len(tickers)``, or ``s in tickers``, when it's relevant to use these.

    But any Tickers object will allow access to any ticker symbol,
    regardless if it's in the ticker_symbols collection or not.

    >>> tickers = Tickers(ticker_symbols=('GOOG', 'AAPL', 'AMZN'))
    >>> assert list(tickers) == ['GOOG', 'AAPL', 'AMZN']
    >>> assert len(tickers) == 3
    >>> assert 'AAPL' in tickers
    >>> assert 'NFLX' not in tickers
    >>> # and yet we have access to NFLX info
    >>> assert tickers['NFLX']['info']['shortName'] == 'Netflix, Inc.'
    """

    def __init__(self,
                 ticker_symbols: Union[str, Iterable] = 'local_list',
                 **kwargs_for_method_keys):
        """
        Make a dict-like container of tickers.

        :param ticker_symbols: A source of ticker symbol strings.
            Could be an explicit list/set of ticker symbol strings.
            Could be a file path to a pickle of such a list.
            Default is "local_list" which will use the list contained in the packages "data/tickers.csv" file.

        Tip: If order doesn't matter to you, specify ticker_symbols as a set,
        since this will accelerate containment checking.
        """
        self._ticker_source_kind = None
        self.kwargs_for_method_keys = kwargs_for_method_keys
        if isinstance(ticker_symbols, str):
            if ticker_symbols == 'local_list':
                self._ticker_source_kind = "local_list"
                self.ticker_symbols = get_local_ticker_list()
            elif os.path.isfile(ticker_symbols):
                self._ticker_source_kind = "filepath of a pickled iterable"
                import pickle
                self.ticker_symbols = pickle.load(open(ticker_symbols))
            else:
                raise ValueError(f"Unrecognized ticker_symbols string. "
                                 f"Should be 'local_list' or the file path of a pickled list. "
                                 f"Was {ticker_symbols}")
        elif isinstance(ticker_symbols, Iterable):
            if len(ticker_symbols) > 7:
                self._ticker_source_kind = f"explicit {type(ticker_symbols)} of {len(ticker_symbols)} tickers"
            self.ticker_symbols = ticker_symbols
        else:
            raise ValueError(f"Unrecognized ticker source. Should be an iterable of explicit or point to one somehow")
        assert isinstance(self.ticker_symbols, Iterable), "self.ticker_symbols should be iterable at this point"

    def __iter__(self):
        yield from self.ticker_symbols

    def __getitem__(self, k):
        return Ticker(k, **self.kwargs_for_method_keys)

    def __contains__(self, k):
        return k in self.ticker_symbols

    def __len__(self):
        return len(self.ticker_symbols)

    def __repr__(self):
        suffix = ""
        if self.kwargs_for_method_keys:
            suffix = f", {_nice_kv_string(self.kwargs_for_method_keys)}"
        if self._ticker_source_kind is not None:
            return f"{type(self).__name__}(ticker_symbols=<{self._ticker_source_kind}>{suffix})"
        else:
            return f"{type(self).__name__}(ticker_symbols={self.ticker_symbols}{suffix})"

    help_me_with = staticmethod(help_me_with)


# TODO: Use py2store explicit tools
@add_ipython_key_completions
class Ticker(KvReader):
    # Note: Subclasses could define this to get sub-stores of base Ticker
    _property_keys = _ticker_attrs_that_are_properties
    _method_keys = _ticker_attrs_that_are_methods

    def __init__(self, ticker_symbol: str,
                 **kwargs_for_method_keys):
        """
        A dict-like interface to ticker information.

        :param ticker_symbol: The ticker symbol string
        :param kwargs_for_method_keys: a key=value specification of the arguments you want to use for "method keys".
            Method keys are keys that point to methods of the underlying yfinance.Ticker object.
            The arguments of these methods all have defaults, but if you want to use different defaults,
            you can specify that here.

        """
        self.ticker_symbol = ticker_symbol
        self.ticker = yf.Ticker(ticker_symbol)
        self._valid_keys = self._property_keys | self._method_keys
        self.kwargs_for_method_keys = kwargs_for_method_keys

    def __iter__(self):
        yield from self._valid_keys

    def __getitem__(self, k):
        try:
            attr = getattr(self.ticker, k)
        except AttributeError:
            if k not in self:
                raise KeyError(f"The valid keys are {self._valid_keys}")
            else:
                raise
        if k in self._property_keys:
            return attr
        elif k in self._method_keys:
            return attr(**self.kwargs_for_method_keys.get(k, {}))

    def __len__(self):
        return len(self._valid_keys)

    def __contains__(self, k):
        return k in self._valid_keys

    def __repr__(self):
        suffix = ""
        if self.kwargs_for_method_keys:
            suffix = f", {_nice_kv_string(self.kwargs_for_method_keys)}"
        return f"{type(self).__name__}('{self.ticker_symbol}'{suffix})"

    help_me_with = staticmethod(help_me_with)


# TODO: Generalize the [:][specific] pattern into a tool and use it.
class TickersWithSpecificInfo(Tickers):
    def __init__(self, ticker_symbols='local_list',
                 specific_key: str = 'info',
                 val_trans: Optional[Callable] = None,
                 **kwargs_for_specific_method):
        """
        A dict-like interface to specific ticker information.

        :param ticker_symbols: A source of ticker symbol strings.
            Could be an explicit list/set of ticker symbol strings.
            Could be a file path to a pickle of such a list.
            Default is "local_list" which will use the list contained in the packages "data/tickers.csv" file.
        :param specific_key: A specific key to use to get information for tickers
        :param val_trans: An optional function to transform the values
        :param kwargs_for_specific_method: a key=value specification of the arguments you want to use
            when the specific_key is a for "method key".
            Method keys are keys that point to methods of the underlying yfinance.Ticker object.
            The arguments of these methods all have defaults, but if you want to use different defaults,
            you can specify that here.

        """
        assert specific_key in _ticker_attrs_that_are_properties or specific_key in _ticker_attrs_that_are_methods, \
            f"Unrecognized specific_key. Needs to be one of these: " \
            f"{_ticker_attrs_that_are_properties | _ticker_attrs_that_are_methods}"
        super().__init__(ticker_symbols=ticker_symbols, **{specific_key: kwargs_for_specific_method})
        self.specific_key = specific_key
        self.val_trans = val_trans
        self.kwargs_for_specific_method = kwargs_for_specific_method

    def __getitem__(self, k):
        obj = super().__getitem__(k)[self.specific_key]
        if self.val_trans is None:
            return obj
        else:
            return self.val_trans(obj)

    def __repr__(self):
        suffix = ""
        if self.kwargs_for_specific_method:
            suffix = f", {_nice_kv_string(self.kwargs_for_specific_method)}"
        suffix = f", specific_key={self.specific_key}, val_trans={self.val_trans}" + suffix
        if self._ticker_source_kind is not None:
            return f"{type(self).__name__}" \
                   f"(ticker_symbols=<{self._ticker_source_kind}>{suffix})"
        else:
            return f"{type(self).__name__}" \
                   f"(ticker_symbols={self.ticker_symbols}{suffix})"

    help_me_with = staticmethod(help_me_with)
