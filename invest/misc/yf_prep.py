import re
import pandas as pd
from py2store import cache_iter, filt_iter, wrap_kvs, kvhead, groupby, ihead, lazyprop
from py2store import KvReader

from invest.dacc import TickerData
from invest.dacc import proj_file
from invest.util import print_progress

from invest.util import is_bsonizable, DFLT_DATE_FORMAT


def asis(x):
    return x


def df_to_dict(x):
    return x.to_dict()


def holders_df(x):
    return x.set_index('Holder').to_dict()


def convert_df_with_timestamp_rows(df):
    return {colname.strftime(DFLT_DATE_FORMAT): dict(colval, Date=colname) for colname, colval in df.to_dict().items()}


def convert_df_as_dict_list_with_index(df):
    return {'records': df.reset_index(drop=False).to_dict(orient='records')}


def convert_df_as_dict_list_without_index(df):
    return {'records': df.to_dict(orient='records')}


def conversion_scanner(data_store,
                       try_keys,
                       try_converters=(
                               asis, df_to_dict, convert_df_with_timestamp_rows, convert_df_as_dict_list_with_index),
                       if_not_found='print_key'):
    """
    # >>> dict(conversion_scanner(data_store=ldata, try_keys=map(ihead, keys_by_kind.values())))
    """
    for k in try_keys:
        v = data_store[k]
        ticker_symbol, data_kind = k
        working_converter = None
        for converter in try_converters:
            try:
                if is_bsonizable(converter(v)):
                    working_converter = converter
                    break
            except Exception as e:
                pass
        if working_converter is not None:
            yield data_kind, working_converter
        else:
            if if_not_found == 'print_key':
                print(f"Didn't manage to convert value for: {k}")


# with conversion_scanner(...) got:
converter_for_data_kind = {
    'quarterly_financials': convert_df_with_timestamp_rows,
    'quarterly_balance_sheet': convert_df_with_timestamp_rows,
    'quarterly_cashflow': convert_df_with_timestamp_rows,
    'cashflow': convert_df_with_timestamp_rows,
    'institutional_holders': convert_df_as_dict_list_without_index,
    'info': asis,
    'dividends': convert_df_as_dict_list_with_index,
    'mutualfund_holders': convert_df_as_dict_list_without_index,
    'quarterly_earnings': convert_df_as_dict_list_with_index,
    'actions': convert_df_as_dict_list_with_index,
    'financials': convert_df_with_timestamp_rows,
    'earnings': convert_df_as_dict_list_with_index
}

key_wrap = wrap_kvs(key_of_id=lambda x: tuple(x.split('/')),
                    id_of_key='/'.join)


@key_wrap
@cache_iter
class LocalData(TickerData):
    pass


def copy_local_to_mongo():
    keys_that_had_empty_vals = set()
    malformed_val_record = dict()

    ldata = LocalData()

    for i, (k, v) in enumerate(ldata.items()):
        try:
            print_progress(f"{i=}: {k}")
            if v is not None and len(v) > 0:
                ticker_symbol, data_kind = k
                mongo_key = {'_id': ticker_symbol}
                if mongo_key in yf[data_kind]:
                    del yf[data_kind][mongo_key]
                if mongo_key not in yf[data_kind]:
                    converter = converter_for_data_kind[data_kind]
                    yf[data_kind][mongo_key] = converter(v)
            else:
                print(f"--> Empty value, deleting ldata[{k}]...")
                keys_that_had_empty_vals.add(k)
                del ldata[k]
        except Exception as e:
            malformed_val_record[k] = e
            print(f"!!! Error with {k}: {e}")


def mgc_to_df(mgc):
    return pd.DataFrame([dict(ticker=k['_id'], **v) for k, v in mgc.items()]).set_index('ticker')


def mgc_to_prepped_data(mgc):
    df = mgc_to_df(mgc)
    if list(df.columns) == ['records']:
        df = df['records']
    return df


from mongodol import MongoDbReader, MongoCollectionPersister
from py2store.caching import mk_cached_store

yf = MongoDbReader('yf', mk_collection_store=MongoCollectionPersister)


@mk_cached_store
@wrap_kvs(obj_of_data=mgc_to_df)
class DbDf(MongoDbReader):
    def __init__(self):
        super().__init__('yf', mk_collection_store=MongoCollectionPersister)


def file_to_field_groups(file=proj_file('misc', 'field_groups_01.xlsx')):
    picks_df = pd.read_excel(file)

    p = re.compile('[\w\s:]+')

    def triples(jerome):
        for x in picks_df.iloc[:, 1].dropna().values:
            yield list(map(str.strip, p.findall(x)))

    picks = groupby(filter(lambda x: len(x) == 3, triples(picks_df)),
                    key=lambda x: x[0],
                    val=lambda x: x[2])

    return picks
