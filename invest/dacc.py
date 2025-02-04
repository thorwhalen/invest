"""
Data access components for the invest package.
"""

import os
from typing import Union, Tuple

from dol.filesys import ensure_slash_suffix
from dol.caching import mk_sourced_store
from dol.paths import str_template_key_trans
from dol import (
    Pipe,
    PickleFiles as LocalPickleStore,  # was from py2store
    add_ipython_key_completions,
    kv_wrap,
    wrap_kvs,
    mk_dirs_if_missing,
)

from invest import Ticker
from invest.util import handle_missing_dir

ROOTDIR_ENVVAR = 'INVEST_ROOTDIR'
DFLT_ROOTDIR = os.environ.get(ROOTDIR_ENVVAR, os.path.expanduser('~/.invest'))
DFLT_TICKER_DATA_DIR = os.path.join(DFLT_ROOTDIR, 'ticker_data')

proj_root_dir = DFLT_ROOTDIR
handle_missing_dir(proj_root_dir)


def proj_file(*args):
    return os.path.join(proj_root_dir, *args)


path_sep = os.path.sep

remote_field_trans = str_template_key_trans(
    '{ticker}' + path_sep + '{field}', str_template_key_trans.key_types.str
)


@kv_wrap(remote_field_trans)
class _RemoteYfDataReader:
    def __getitem__(self, k):
        ticker_symbol, field = k.split(path_sep)
        return Ticker(ticker_symbol)[field]


remote_data = _RemoteYfDataReader()

ticker_field_trans = str_template_key_trans(
    '{ticker}' + path_sep + '{field}.p', str_template_key_trans.key_types.str
)


@add_ipython_key_completions
@kv_wrap(ticker_field_trans)
@mk_dirs_if_missing
class LocalTickerData(LocalPickleStore):
    def __init__(self, ticker_data_dir=DFLT_TICKER_DATA_DIR):
        handle_missing_dir(ticker_data_dir)
        super().__init__(ensure_slash_suffix(ticker_data_dir), max_levels=1)


_YahooData = mk_sourced_store(
    store=LocalTickerData,
    source=remote_data,
    return_source_data=True,
    __name__='_YahooData',
    __module__=__name__,
)


def join_tuples_with_sep(k: Union[str, Tuple[str]]) -> str:
    if isinstance(k, tuple):
        return path_sep.join(k)
    return k


def default_to_history(k: str) -> str:
    if path_sep not in k:
        return k + path_sep + 'history'
    return k


@add_ipython_key_completions
@wrap_kvs(key_encoder=Pipe(join_tuples_with_sep, default_to_history))
class TickerData(_YahooData):
    """
    A store that can get data from Yahoo Finance, and store it locally.

    The process is the usual read-through process.
    If the data is in the local store, it is read from there.
    If it's not, it is read from the source (Yahoo Finance) and stored locally.

    >>> td = TickerData()  # doctest: +SKIP
    >>> td['NVDA/history']  # doctest: +SKIP
                    Open        High         Low       Close     Volume  Dividends  Stock Splits
    Date
    2025-01-06  148.589996  152.160004  147.820007  149.429993  265377400        0.0           0.0
    2025-01-07  153.029999  153.130005  140.009995  140.139999  351782200        0.0           0.0
    ...
    2025-01-31  123.779999  127.849998  119.190002  120.070000  390372900        0.0           0.0
    2025-02-03  114.750000  118.570000  113.010002  116.660004  369021900        0.0           0.0
    """

    def __init__(self, ticker_data_dir=DFLT_TICKER_DATA_DIR):
        handle_missing_dir(ticker_data_dir)
        super().__init__(ticker_data_dir=ensure_slash_suffix(ticker_data_dir))
