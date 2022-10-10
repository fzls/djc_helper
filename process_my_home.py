# 10折 1200 VDMzZFF1T0hKdTRjaEJRMkV0N2xiZz09 (0/3) 舞***影(15***33)

def extract_price(share_str: str) -> int:
    return int(share_str.split(" ")[1])


def extract_suin(share_str: str) -> str:
    return share_str.split(" ")[2]


def extract_remaining_times(share_str: str) -> int:
    # (0/3)
    temp = share_str.split(" ")[3][1:-1]
    remaing_times = int(temp.split("/")[0])

    return remaing_times


# 清洗并去重
with open(".cached/my_home.csv", "r", encoding="utf-8") as f:
    suin_to_share_str = {}

    f.readline()
    for line in f:
        line = line.strip()

        if line == "":
            continue
        if line.endswith("自己"):
            continue

        suin = extract_suin(line)
        if suin in suin_to_share_str:
            last_info = suin_to_share_str[suin]
            if extract_remaining_times(line) <= extract_remaining_times(last_info):
                # 之前记录的是新一点的数据
                continue

        suin_to_share_str[suin] = line

# 排序
share_str_list = []
for s in suin_to_share_str.values():
    share_str_list.append(s)
share_str_list.sort(key=lambda s: extract_price(s))

# 导出
from datetime import datetime

with open(".cached/my_home_processed.csv", "w", encoding="utf-8") as f:
    f.write(f"{datetime.now()} 总计：{len(share_str_list)}个\n")
    for share_str in share_str_list:
        f.write(share_str + "\n")
