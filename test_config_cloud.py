from config_cloud import TryAutoUpdateIgnorePermissionConfig
from util import parse_time


def test_can_ignore():
    # 准备测试环境
    cfg = TryAutoUpdateIgnorePermissionConfig()
    cfg.latest_bug_fixed_version = "1.0.1"
    cfg.period_list = [
        ("2023-02-05 00:00:00", "2023-02-15 00:00:00"),
    ]

    version_has_bug = "1.0.0"
    version_ok = "1.0.2"

    time_out_of_range = parse_time("2023-02-01 00:00:00")
    time_in_range = parse_time("2023-02-10 00:00:00")

    assert cfg.can_ignore(version_has_bug, time_out_of_range)
    assert cfg.can_ignore(version_has_bug, time_in_range)
    assert not cfg.can_ignore(version_ok, time_out_of_range)
    assert cfg.can_ignore(version_ok, time_in_range)

    # 测试默认情况下应任何组合都无法触发
    default_cfg = TryAutoUpdateIgnorePermissionConfig()
    assert not default_cfg.can_ignore(version_has_bug, time_out_of_range)
    assert not default_cfg.can_ignore(version_has_bug, time_in_range)
    assert not default_cfg.can_ignore(version_ok, time_out_of_range)
    assert not default_cfg.can_ignore(version_ok, time_in_range)
