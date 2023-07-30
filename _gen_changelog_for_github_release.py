"""将CHANGELOG.MD中的本次更新信息提取出来，供github release流程使用"""
from __future__ import annotations

import os.path

from log import logger
from util import make_sure_dir_exists


def gen_changelog():
    update_message_list: list[str] = []

    # 解析changelog文件
    version_list: list[str] = []
    version_to_update_message_list: dict[str, list[str]] = {}
    with open("CHANGELOG.MD", encoding="utf-8") as changelog_file:
        version = ""
        for line in changelog_file:
            # # v20.0.1 2022.8.22
            if line.startswith("# v"):
                version = line.split(" ")[1][1:]
                version_list.append(version)
                continue

            if version != "":
                if version not in version_to_update_message_list:
                    version_to_update_message_list[version] = []
                version_to_update_message_list[version].append(line.strip())

    # 获取需要的版本信息
    latest_version = version_list[0]
    update_message_list.extend(version_to_update_message_list[latest_version])

    # 导出文本
    github_release_dir = os.path.realpath("./releases/_github_action_artifact")
    make_sure_dir_exists(github_release_dir)

    github_change_path = os.path.join(github_release_dir, "changelog-github.txt")
    logger.info(f"将更新信息写入临时文件，供github release使用: {github_change_path}")
    with open(github_change_path, "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(update_message_list))


if __name__ == '__main__':
    gen_changelog()
