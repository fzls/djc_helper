import datetime
import random
import time

from first_run import is_first_run_in


def test_is_first_run_in():
    # 修复bug: 原先用update，每次save都会更新该值，导致如果两次判断间隔在该时间范围内，而第二次应该已经超过对应时间的时候，仍旧返回该范围内已运行过的bug
    # 如间隔为1秒，在第一次检查后，之后分别在0.6秒和1.2秒的时候去检查，正确的结果应该分别是False和True，但是之前的bug会导致全是False
    test_key = f"test_is_first_run_in_{time.time()}_{random.random()}"
    test_seconds = 0.5
    duration = datetime.timedelta(seconds=test_seconds)

    assert is_first_run_in(test_key, duration) is True
    time.sleep(0.6 * test_seconds)
    assert is_first_run_in(test_key, duration) is False
    time.sleep(0.6 * test_seconds)
    assert is_first_run_in(test_key, duration) is True
