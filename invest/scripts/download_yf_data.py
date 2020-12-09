import pickle
import os

from invest import dacc
from invest import get_local_ticker_set
from invest.util import print_progress

DFLT_FIELDS = (
    #     'info',
    #     'financials',
    #     'institutional_holders',
    # 'mutualfund_holders',
    # 'actions',
    # 'quarterly_balance_sheet',
    # 'quarterly_cashflow',
    # 'quarterly_earnings',
    # 'quarterly_financials',
    # 'dividends',
    'earnings',
    'balance_sheet',
    'cashflow',
    'history',
)


def download_yf_data(local_ticker_data=dacc.LocalTickerData(),
                     ticker_symbols=tuple(sorted(get_local_ticker_set())),
                     fields=DFLT_FIELDS,
                     except_keys=None,
                     error_tickers_save_filepath='bad_ticker_info',
                     on_error_add_to_except_keys=True,
                     ):
    # handle except_keys
    if except_keys is None and os.path.isfile(error_tickers_save_filepath):
        with open(error_tickers_save_filepath, 'rb') as fp:
            except_keys = pickle.load(fp)
    elif isinstance(except_keys, str):
        try:
            with open(except_keys, 'rb') as fp:
                except_keys = pickle.load(fp)
        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")
            except_keys = {}
    else:
        except_keys = {}

    except_keys = set(except_keys)

    # and now do the thing
    def handle_key_exception(key, error, except_keys):
        print(f"Error with {key}: {error}")
        except_keys.add(on_error_add_to_except_keys)

    key = None  # to define and appease linter
    try:
        for field in fields:
            for i, ticker_symbol in enumerate(ticker_symbols, 1):
                try:
                    key = f"{ticker_symbol}/{field}"
                    if key not in except_keys and key not in local_ticker_data:
                        print_progress(f"{i}: {key}")
                        local_ticker_data[key] = dacc.remote_data[key]
                except Exception as e:
                    handle_key_exception(key, e, except_keys)
    finally:
        print(f"Current key is {key}")
        print(f"Saving {len(except_keys)} except_keys tickers to on_error_add_to_except_keys file")
        with open(error_tickers_save_filepath, 'wb') as fp:
            pickle.dump(except_keys, fp)


download_yf_data()