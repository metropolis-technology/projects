import order_execution
import time

def test_short():
    s = order_execution.Session('GBP', 'CHF', long=False, base_USD=10000, total_hours=.1, interval=5)

    check1 = order_execution.CheckPoint(time.time() + 60, order_execution.CheckPoint.TYPE_NORMAL)
    check2 = order_execution.CheckPoint(time.time() + 120, order_execution.CheckPoint.TYPE_CALCULATE_ONLY)
    check3 = order_execution.CheckPoint(time.time() + 150, order_execution.CheckPoint.TYPE_LAST)
    s.add_check_point(check1)
    s.add_check_point(check2)
    s.add_check_point(check3)

    s.trade()

    print(s.get_profit_usd())
    print(s.get_rates_DF())
    print(s.get_failed_rows_DF())


def test_medium():
    s = order_execution.Session('GBP', 'CHF')

    check1 = order_execution.CheckPoint(time.time() + 60, order_execution.CheckPoint.TYPE_NORMAL)
    check2 = order_execution.CheckPoint(time.time() + 120, order_execution.CheckPoint.TYPE_CALCULATE_ONLY)
    check3 = order_execution.CheckPoint(time.time() + 150, order_execution.CheckPoint.TYPE_LAST)
    s.add_check_point(check1)
    s.add_check_point(check2)
    s.add_check_point(check3)

    s.trade()

    print(s.get_profit_usd())
    print(s.get_rates_DF())
    print(s.get_failed_rows_DF())

# Default
def test_long():
    s = order_execution.Session('GBP', 'CHF')

    check1 = order_execution.CheckPoint(time.time() + 4 * 60 * 60, order_execution.CheckPoint.TYPE_NORMAL)
    check2 = order_execution.CheckPoint(time.time() + (4 + 6) * 60 * 60 - 5 * 60, order_execution.CheckPoint.TYPE_CALCULATE_ONLY)
    check3 = order_execution.CheckPoint(time.time() + (4 + 6) * 60 * 60, order_execution.CheckPoint.TYPE_LAST)
    s.add_check_point(check1)
    s.add_check_point(check2)
    s.add_check_point(check3)

    s.trade()

    print(s.get_profit_usd())
    print(s.get_rates_DF())
    print(s.get_failed_rows_DF())



if __name__ == '__main__':
    test_long()