import re


def format_changelog(changelog_text: str) -> str:
    """
    用于解决新版本的 pycharm 中不再会自动调整md中的列表编号的问题，避免手动一个个调整
    """
    formatted_items = []

    item_reg = r"\d+\. (.+)"
    current_index = 1
    lines = changelog_text.strip().splitlines()
    for current_line in lines:
        current_line = current_line.strip()
        match = re.match(item_reg, current_line)
        if match is None:
            # 非具体条目，原样输出
            formatted_items.append(current_line)
            continue

        info = match.group(1)
        re_numbered_line = f"{current_index}. {info}"
        formatted_items.append(re_numbered_line)

        current_index += 1

    return "\n".join(formatted_items)


if __name__ == "__main__":
    changelog_text = """
1. 更新内容 - 1
7. 更新内容 - 2
8. 更新内容 - 3
12. 更新内容 - 4
    """

    formated_changelog = format_changelog(changelog_text)
    print(formated_changelog)
