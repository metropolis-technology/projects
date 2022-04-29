import debug
from polygon import RESTClient
import time
from collections import namedtuple

DEFAULT_KEY = "beBybSi8daPgsTp5yx5cHtHpYcrjp5Jq"

ExRateRow = namedtuple("ExRateRow", ['timestamp', 'pair', 'rate'])

def failed_row(timestamp, pair):
    return ExRateRow(timestamp, pair, 0)

def is_failed_row(row: "ExRateRow"):
    return row.rate == 0

def __call_api_base(currency1, currency2, key = None, amount = 1, precision = 4):
    if key is None:
        key = DEFAULT_KEY

    with RESTClient(key) as client:
        data = client.forex_currencies_real_time_currency_conversion(
            currency1, currency2, amount = amount, precision = precision)

        ex_rate = (data.last['ask'] + data.last['bid'])/2
        if (data.converted < amount) != (ex_rate < 1): # xor
            # currency1 worth less than currency2
            ex_rate = 1 / ex_rate
        row = ExRateRow(data.last['timestamp'], f"{currency1}{currency2}", ex_rate)

    return row


def call_api(currency1, currency2, key = None, amount = 1, precision = 4):
    try:
        return __call_api_base(currency1, currency2, key, amount, precision)
    except Exception as e:
        t = time.time()
        t_human = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t))
        debug.log(f"Error when local time {t_human}, epoch time: {t}")
        debug.log(e)
        return failed_row(t, pair = f"{currency1}{currency2}")


def call_api_timeout(currency1, currency2, key = None, amount = 1, precision = 4, timeout = 5, sleep = 1):
    if sleep < 1:
        raise RuntimeError(f"Request too frequent! {sleep}")
    
    curr_time = time.time()
    next_time = curr_time + timeout

    while time.time() < next_time:
        row = call_api(currency1, currency2, key, amount, precision)
        if row is not None:
            return row
        
        time.sleep(sleep)
    
    debug.log("Time out")
    return failed_row(time.time(), pair = f"{currency1}{currency2}")