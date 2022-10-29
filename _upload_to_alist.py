from __future__ import annotations

# 上传相关文件到alist
import os

from alist import upload
from log import color, logger
from version import now_version


def upload_to_alist(files_to_upload: list[tuple[str, str]]):
    logger.info(color("bold_yellow") + f"将上传下列文件到alist: {files_to_upload}")

    for file_path, old_version_name_prefix in files_to_upload:
        upload(file_path, old_version_name_prefix=old_version_name_prefix)


def main():
    dir_src = os.path.realpath(".")
    dir_all_release = os.path.realpath(os.path.join("releases"))
    release_prefix = "DNF蚊子腿小助手_v"
    release_7z_path = os.path.join(dir_all_release, f"{release_prefix}{now_version}_by风之凌殇.7z")

    upload_to_alist([
        (release_7z_path, release_prefix),
    ])


if __name__ == "__main__":
    main()
