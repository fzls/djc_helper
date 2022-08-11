import json
import os
import time

from auto_updater import extract_decompressed_directory_name
from compress import compress_dir_with_py7zr, decompress_dir_with_py7zr
from const import downloads_dir
from download import download_latest_github_release
from log import logger


def main():
    # 供机器人自动上传新版本到群文件使用

    logger.info("从github下载最新版本")
    filepath = download_latest_github_release(downloads_dir)
    logger.info(f"最新版本路径为 {filepath}")

    logger.info("解压出里面带版本号的目录，并获得其路径")
    decompress_dir_with_py7zr(filepath, dst_parent_folder=downloads_dir)
    target_dir = extract_decompressed_directory_name(filepath)
    logger.info(f"目标目录为 {target_dir}")

    cwd = os.getcwd()
    os.chdir(downloads_dir)

    logger.info("再次压缩，得到最终的压缩包")
    final_7z_path = target_dir + ".7z"
    compress_dir_with_py7zr(target_dir, final_7z_path)
    logger.info(f"最终压缩包为 {final_7z_path}")

    os.chdir(cwd)

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
