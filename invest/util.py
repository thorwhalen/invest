from typing import Iterable

DFLT_TICKER = "GOOG"


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
        _getless_callable_attrs,
        _ticker_attrs_that_are_properties,
    )
    assert _getless_callable_attrs.issubset(_ticker_attrs_that_are_properties), "Some callable attrs were lost"
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
