import os

from py2store import LocalPickleStore
from py2store.stores.local_store import AutoMkDirsOnSetitemMixin
from py2store.persisters.local_files import ensure_slash_suffix
from py2store.caching import mk_sourced_store
from py2store.trans import add_ipython_key_completions, kv_wrap
from py2store.key_mappers.paths import str_template_key_trans

from invest import Ticker
from invest.util import handle_missing_dir

ROOTDIR_ENVVAR = 'INVEST_ROOTDIR'
DFLT_ROOTDIR = os.environ.get(ROOTDIR_ENVVAR, os.path.expanduser('~/.invest'))
DFLT_TICKER_DATA_DIR = os.path.join(DFLT_ROOTDIR, 'ticker_data')

handle_missing_dir(DFLT_ROOTDIR)

path_sep = os.path.sep

remote_field_trans = str_template_key_trans('{ticker}' + path_sep + '{field}', str_template_key_trans.key_types.str)


@kv_wrap(remote_field_trans)
class _RemoteYfDataReader:
    def __getitem__(self, k):
        ticker_symbol, field = k.split(path_sep)
        return Ticker(ticker_symbol)[field]


remote_data = _RemoteYfDataReader()

ticker_field_trans = str_template_key_trans('{ticker}' + path_sep + '{field}.p', str_template_key_trans.key_types.str)


@add_ipython_key_completions
@kv_wrap(ticker_field_trans)
class LocalTickerData(AutoMkDirsOnSetitemMixin, LocalPickleStore):
    def __init__(self, ticker_data_dir=DFLT_TICKER_DATA_DIR):
        handle_missing_dir(ticker_data_dir)
        super().__init__(path_format=ensure_slash_suffix(ticker_data_dir), max_levels=1)


_YahooData = mk_sourced_store(
    store=LocalTickerData,
    source=remote_data,
    return_source_data=True,
    __name__='_YahooData',
    __module__=__name__
)


@add_ipython_key_completions
class TickerData(_YahooData):
    def __init__(self, ticker_data_dir=DFLT_TICKER_DATA_DIR):
        handle_missing_dir(ticker_data_dir)
        super().__init__(ticker_data_dir=ensure_slash_suffix(ticker_data_dir))
