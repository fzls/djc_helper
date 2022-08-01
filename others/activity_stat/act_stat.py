from __future__ import annotations

from collections import Counter
from datetime import datetime

# 解析活动数据
act_info_list: list[tuple[str, str]] = []

with open("短期活动统计.csv", "r", encoding="utf-8") as input_file:
    input_file.readline()

    for line in input_file:
        date_str, name = line.strip().split(" ", 1)

        act_info_list.append((date_str, name))

# 统计活动次数
day_to_act_count = Counter()
month_to_act_count = Counter()
for date_str, name in act_info_list:
    month_str = date_str[:-3]

    day_to_act_count[date_str] += 1
    month_to_act_count[month_str] += 1

# 输出统计结果
with open("按日统计.csv", "w", encoding="utf-8") as output_file:
    for day, count in day_to_act_count.items():
        output_file.write(f"{day}\t{count}\n")

with open("按月统计.csv", "w", encoding="utf-8") as output_file:
    for month, count in month_to_act_count.items():
        output_file.write(f"{month}\t{count}\n")
