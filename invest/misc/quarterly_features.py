"""
Module to extract, prepare, and produce feature vectors for quarterly stock data.
"""
from datetime import datetime as dt
import itertools
import re
from collections import Counter
from operator import itemgetter

import pandas as pd
import numpy as np

from py2store import lazyprop
from py2store import StrTupleDict
from py2store import groupby

from i2.deco import postprocess

from invest.misc.yf_prep import DbDf

qy_parser = StrTupleDict('{quarter}Q{year}',
                         {'quarter': '\d', 'year': '\d\d\d\d'},
                         process_info_dict={'quarter': int, 'year': int}
                         )

month_of_quarter = {1: 1, 2: 4, 3: 7, 4: 10}

not_w_p = re.compile('\W')


def normalize_str(string):
    return not_w_p.sub('_', string.lower())


def indices_counts(ser: pd.Series):
    return Counter(itertools.chain.from_iterable(x.index.values for x in ser))


def number_of_quarters_counts(ser: pd.Series):
    return Counter(len(x) for x in ser)


def trans_quarter(string):
    """Transform from (not lexicographic friendly) {quarter}Q{year} to a datetime object.
    >>> trans_quarter('4Q2019')
    datetime.datetime(2019, 10, 1, 0, 0)
    """
    quarter, year = qy_parser.str_to_tuple(string)
    return dt(year=year, month=month_of_quarter[quarter], day=1)


def to_quarter_df(arr, cols=None):
    ser = pd.Series({trans_quarter(x['Quarter']): x for x in arr})
    df = pd.DataFrame.from_records(ser, index=ser.index)
    if cols:
        return df[cols]
    else:
        return df


def prep_quarterly_earnings(quarterly_earnings: pd.Series, cols=None):
    sr = pd.Series({ticker: to_quarter_df(d, cols) for ticker, d in quarterly_earnings['records'].items()})
    return sr.sort_index()


def prep_quarterly_from_df(df: pd.DataFrame):
    def gen():
        for ticker, row in df.sort_index(axis=1).iterrows():
            row = row.dropna()
            d = pd.DataFrame.from_records([x for x in row.values], index=row.index)
            if 'Date' in d.columns:
                del d['Date']
            yield ticker, d.fillna(np.nan)

    return pd.Series(dict(gen()))


def quarter_data_features(quarter_value_seq, n=2):
    """Quarterly data features. Assumes that quarter_value_seq has been sorted by time"""
    s = np.array(quarter_value_seq)  # copy and/or make into array

    m0 = np.mean(s)
    if n >= 2:
        s = s / abs(m0)  # normalize out m0 from s
        m1 = np.mean(np.diff(s, 1))
    if n == 3:
        s = s / abs(m1)  # normalize out m1 from s
        m2 = np.mean(np.diff(s, 2))
        return m0, m1, m2
    elif n == 2:
        return m0, m1
    elif n == 1:
        return (m0,)
    else:
        raise ValueError(f"n should be 1, 2 or 3 (was {n})")


def quarter_feature_gen(quarter_items, cols=None):
    for ticker, df in quarter_items:
        if cols is None:
            _cols = df.columns
        else:
            _cols = cols
        for k in _cols:
            for i, v in enumerate(quarter_data_features(df[k])):
                if v is not None and not np.isnan(v):
                    yield ticker, f"q_{normalize_str(k)}_{i}", v


#                 yield dict(ticker=ticker, **{f"q_{normalize_str(k)}_{i}": v})

def ticker_featname_featval_iterable_to_df(triple_iterable):
    d = {k: dict(v) for k, v in groupby(triple_iterable, key=itemgetter(0), val=itemgetter(1, 2)).items()}
    return pd.DataFrame(d).T


class Dacc:
    quarterly_earnings_cols = ['Revenue', 'Earnings']

    def __init__(self):
        self.db = DbDf()

    def __iter__(self):
        yield from self.db

    @lazyprop
    def quarterly_earnings(self):
        data = self.db['quarterly_earnings']
        return prep_quarterly_earnings(data, self.quarterly_earnings_cols)

    @lazyprop
    def quarterly_balance_sheet(self):
        return prep_quarterly_from_df(self.db['quarterly_balance_sheet'])

    @lazyprop
    def quarterly_cashflow(self):
        return prep_quarterly_from_df(self.db['quarterly_cashflow'])

    @lazyprop
    def quarterly_financials(self):
        return prep_quarterly_from_df(self.db['quarterly_financials'])

    def features_gen(self):
        yield from quarter_feature_gen(self.quarterly_earnings.items(), self.quarterly_earnings_cols)
        yield from quarter_feature_gen(self.quarterly_balance_sheet.items())
        yield from quarter_feature_gen(self.quarterly_cashflow.items())
        yield from quarter_feature_gen(self.quarterly_financials.items())

    @lazyprop
    def features_df(self):
        return ticker_featname_featval_iterable_to_df(self.features_gen())
