"""
util.py for invest package
"""

import io
import os
from typing import Iterable
from datetime import datetime

import requests as _requests

DFLT_TICKER = "GOOG"
DFLT_DATE_FORMAT = '%Y-%m-%d:%H:%M:%S'

DFLT_REQUEST_HEADER = {'User-Agent': 'Mozilla/5.0'}


def requests_get(*args, headers=DFLT_REQUEST_HEADER, **kwargs):
    response = _requests.get(*args, headers=headers, **kwargs)
    if not response.ok:
        response.raise_for_status()
    return response


def read_html(url, **kwargs):
    import pandas as pd

    reponse = requests_get(url, **kwargs)
    return pd.read_html(io.StringIO(reponse.text))


def hms_message(msg=''):
    t = datetime.now()
    return "({:02.0f}){:02.0f}:{:02.0f}:{:02.0f} - {}".format(
        t.day, t.hour, t.minute, t.second, msg
    )


def print_progress(msg, refresh=None, display_time=True):
    """
    input: message, and possibly args (to be placed in the message string, sprintf-style
    output: Displays the time (HH:MM:SS), and the message
    use: To be able to track processes (and the time they take)
    """
    if display_time:
        msg = hms_message(msg)
    if refresh is not False:
        print(msg, '\r')
        # stdout.write('\r' + msg)
        # stdout.write(refresh)
        # stdout.flush()
    else:
        print(msg)


def all_info(ticker):
    for k, v in ticker.items():
        if hasattr(v, '__len__'):
            if len(v) > 0:
                yield k, v
        elif v is not None:
            yield k, v


def all_info_printable_string(ticker):
    def gen():
        for k, v in all_info(ticker):
            yield f"\n----------{k}-------------"
            yield f"{v}"

    return '\n'.join(gen())


def _assert_that_attrs_extraction_is_correct():
    from invest.base import (
        Ticker,
        _ticker_attrs_that_are_properties,
    )
    from invest._prep import _getless_callable_attrs

    assert _getless_callable_attrs.issubset(
        _ticker_attrs_that_are_properties
    ), "Some callable attrs were lost"
    ticker = Ticker(DFLT_TICKER)
    for attr in _getless_callable_attrs:
        prop_version = ticker[attr]
        method_version = ticker[f'get_{attr}']
        if isinstance(prop_version, pd.DataFrame):
            comparison = prop_version.fillna(-9) == method_version.fillna(-9)
            comparison = comparison.values.all()
        else:
            comparison = prop_version == method_version

        assertion_error_msg = f"method and prop versions were not the same for {attr}"
        if isinstance(comparison, Iterable):
            assert all(comparison), assertion_error_msg
        else:
            assert comparison, assertion_error_msg


def clog(condition, *args):
    if condition:
        print(*args)


def handle_missing_dir(dirpath, prefix_msg='', ask_first=True, verbose=True):
    if not os.path.isdir(dirpath):
        if ask_first:
            clog(verbose, prefix_msg)
            clog(verbose, f"This directory doesn't exist: {dirpath}")
            answer = input("Should I make that directory for you? ([Y]/n)?") or 'Y'
            if next(iter(answer.strip().lower()), None) != 'y':
                return
        clog(verbose, f"Making {dirpath}...")
        os.mkdir(dirpath)


import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


def is_jsonizable(obj):
    try:
        json.loads(json.dumps(obj))
        return True
    except Exception:
        return False


from typing import Iterable


def is_bsonizable(obj):
    """

    >>> is_bsonizable({"this": 'is normal'})  # also jsonizable
    True
    >>> is_bsonizable({"date": datetime.now()})  # NOT jsonizable
    True
    >>> is_bsonizable({datetime.now(): "datetime objects allowed as values, not keys"})  # also NOT jsonizable
    False

    """
    from bson import json_util

    try:
        json_util.loads(json_util.dumps(obj))
        return True
    except Exception:
        return False
