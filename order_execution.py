import time
import debug
from call_api import call_api, is_failed_row
from call_api import ExRateRow
from collections import deque
import pandas


def hour_to_seconds(h):
    return h * 60 * 60

class CheckPoint:
    TYPE_NORMAL = 0
    TYPE_CALCULATE_ONLY = 1
    TYPE_LAST = 2
    def __init__(self, time, type: int):
        self.time = time
        self.type = type

    def __str__(self) -> str:
        return f"{super().__str__()}: time = {self.time}, type = {self.type}"


class Session:
    # constructor
    ACCEPTABLE_TOTAL_HOURS = (14, 7)
    frame_interval = 1 # in seconds, make sure in sync with interval
    cycle_interval = 0.5 # in seconds, used to sleep

    def __init__(self, currency1: str, currency2: str, long = True, base_USD = 10000, total_hours = 14, interval = 15):
        # if total_hours not in Session.ACCEPTABLE_TOTAL_HOURS:
        #     raise ValueError(f"Invalid Total Hours, pleasee select from {Session.ACCEPTABLE_TOTAL_HOURS}")

        # store the arguments
        self.currency1 = currency1
        self.currency2 = currency2
        self.long = long
        self.base_USD = base_USD
        self.total_hours = total_hours
        self.interval = interval

        # Dynamic growing fields
        self.profit_list = [] # type: list[float]
        self.ex_row_list = [] # type: list["ExRateRow"]
        self.failed_rows = [] # type: list["ExRateRow"]

        self.__ex_sum = 0 # not exposed, help keep track of avg
        self.ex_last_checkpoint = 0
        self.packages_used = 0

        # User should define the checkpoints
        self.checkpoints = deque() # type: deque["CheckPoint"]

        # These are determined after calling self.preprocess()
        self.currency_inhand = None
        self.rate_USD_currency1 = None
        self.package_size = 0
        self.hold = False

        # Run preprocess
        self.preprocess()

    def add_check_point(self, checkpoint: "CheckPoint"):
        self.checkpoints.append(checkpoint)

    # Make sure checkpoints are set
    # Make sure checkpoints are sorted with time
    def validate_checkpoints(self):
        last_time = 0
        for checkpoint in self.checkpoints:
            if checkpoint.time < last_time:
                return False
            last_time = checkpoint.time

        return len(self.checkpoints) > 0
    
    # Average exchange rate (between currency1 and currency2)
    @property
    def __ex_avg(self):
        return self.__ex_sum / len(self.ex_row_list)
    
    # append to ex_row_list and update __ex_sum
    def __ex_record(self, row: "ExRateRow"):
        # TODO: Should I change strategy for failed attempts?

        # Strategy: use mean value
        if is_failed_row(row):
            repalcing_row_rate = self.__ex_avg
            row  = ExRateRow(row.timestamp, row.pair, repalcing_row_rate)
            self.failed_rows.append(row)

        self.ex_row_list.append(row)
        self.__ex_sum += row.rate

    @classmethod
    def from_high_low(cls, currency1, currency2, long = True, base_USD = 10000, highlow = 1, interval = 15) -> "Session":
        total_hours = 7 if highlow == 1 else 14
        return cls(currency1, currency2, long, base_USD, total_hours, interval)

    def preprocess(self):
        if self.currency1 == 'USD':
            self.rate_USD_currency1 = 1
            self.currency_inhand = self.base_USD
        else:
            rate_usd_row = call_api('USD', self.currency1)

            if is_failed_row(rate_usd_row):
                raise RuntimeError(f'Request to initial currency pair {"USD"}{self.currency1}')

            self.rate_USD_currency1 = rate_usd_row.rate

            self.currency_inhand = self.base_USD * self.rate_USD_currency1

        trading_times = (hour_to_seconds(self.total_hours) / self.interval)
        self.package_size = self.currency_inhand / trading_times
    
    def percentage_change(self, current_ex_rate):
        if self.long:
            return (current_ex_rate - self.ex_last_checkpoint) / self.ex_last_checkpoint
        else:
            return - (current_ex_rate - self.ex_last_checkpoint) / self.ex_last_checkpoint

    # only called at check points
    def profit (self, current_ex_rate):
        num_packages = len(self.ex_row_list) - self.packages_used
        package_size_curr = num_packages * self.package_size
        profit = package_size_curr * self.percentage_change(current_ex_rate)
        debug.log(f"\nself.profit: num_packages={num_packages}, package_size_curr={package_size_curr}")
        debug.log(f"self.profit: percentage_change={self.percentage_change(current_ex_rate)}, profit={profit}")
        debug.log("")
        self.packages_used += num_packages
        return profit

    def trade(self):
        # see if checkpoints are set
        if not self.validate_checkpoints():
            raise RuntimeError("Checkpoints are not set.")

        stop = False # tweak at check points
        hold = False
        trade_starting_time = time.time()
        trade_stop_time = trade_starting_time + hour_to_seconds(self.total_hours)

        next_frame_time  = trade_starting_time
        next_trade_time = trade_starting_time # interval time, e.g. next 15 secs

        # TODO: Sleep to avoid 100% CPU
        while not stop:
            if (curr_time := time.time()) > next_frame_time:
                # Check Interval
                if curr_time > next_trade_time and not hold:
                    # record api return
                    ex_row = call_api(currency1=self.currency1, currency2=self.currency2)
                    self.__ex_record(ex_row)
                    # If ex_last_chechpoint is not set, set it to first ex rate
                    if self.ex_last_checkpoint == 0:
                        self.ex_last_checkpoint = ex_row.rate
                    
                    debug.log(f"Trading: {ex_row}")
                    # set next interval time
                    next_trade_time += self.interval

                # Check Checkpoint
                # TODO: check if empty
                if len(self.checkpoints) > 0 and curr_time > self.checkpoints[0].time:
                    check_point_row = call_api(currency1=self.currency1, currency2=self.currency2)
                    # Dont put it into records

                    # All types need to calcualte profit
                    profit = self.profit(check_point_row.rate)
                    # print("Profit in USD: {}".format(profit / self.rate_USD_currency1))
                    self.profit_list.append(profit)

                    # Update last check point
                    self.ex_last_checkpoint = check_point_row.rate

                    curr_type = self.checkpoints[0].type
                    # Set hold flag
                    if curr_type != CheckPoint.TYPE_CALCULATE_ONLY:
                        # Default long
                        is_continue = self.__ex_avg < check_point_row.rate
                        hold = not is_continue
                        if not self.long:
                            hold = not hold

                        if curr_type == CheckPoint.TYPE_LAST:
                            if hold:
                                stop = True

                    debug.log("Checkpoint<")
                    debug.log(str(self.checkpoints[0]))
                    debug.log(f"Profit: {profit}")
                    debug.log(f"Hold/Break?: {hold}")
                    debug.log(">Checkpoint")

                    self.checkpoints.popleft() # throw away the current checkpoint

                # update next frame and see if trading time ends
                next_frame_time += self.frame_interval
                if next_frame_time > trade_stop_time:
                    break
            
            time.sleep(self.cycle_interval)

        self.postprocess()

    def get_profit_usd(self):
        return sum(self.profit_list) / self.rate_USD_currency1
    
    def get_rates_DF(self):
        return pandas.DataFrame(self.ex_row_list)

    def get_failed_rows_DF(self):
        return pandas.DataFrame(self.failed_rows)

    def postprocess(self):
        pass