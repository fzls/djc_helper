import json
import os
import time

from config import CommonConfig
from const import downloads_dir
from download import download_latest_github_release
from log import logger
from update import get_latest_version_from_github


def get_latest_version() -> str:
    # 尝试从github获取版本信息
    cfg = CommonConfig()
    return get_latest_version_from_github(cfg)


def main():
    # 供机器人自动上传新版本到群文件使用

    logger.info("从github下载最新版本")
    github_7z_filepath = download_latest_github_release(downloads_dir)
    logger.info(f"最新版本路径为 {github_7z_filepath}")

    logger.info("获取最新版本号，重命名压缩包")
    latest_version = get_latest_version()

    final_7z_name = f"DNF蚊子腿小助手_v{latest_version}_by风之凌殇.7z"
    final_7z_path = os.path.join(os.path.dirname(github_7z_filepath), final_7z_name)

    logger.info(f"将压缩包重命名为实际的名称: {final_7z_name}")
    if os.path.exists(final_7z_path):
        os.remove(final_7z_path)
    os.rename(github_7z_filepath, final_7z_path)

    logger.info(f"最终路径为: {final_7z_path}")

    # 输出结果，供机器人解析。由于上面部分流程实在没法避免产生日志，所以在结果上加个前后缀，方便定位结果
    logger.info("输出结果")
    boundary_mark = "$$boundary$$"
    json_result = json.dumps(
        {
            "downloaded_path": final_7z_path,
        }
    )

    # 等待一会，确认其他日志全部已输出
    time.sleep(2)
    print(f"{boundary_mark}\n{json_result}\n{boundary_mark}")


if __name__ == "__main__":
    main()
