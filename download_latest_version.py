import json

from const import downloads_dir
from upload_lanzouyun import Uploader


def main():
    uploader = Uploader()

    # 供机器人自动上传新版本到群文件使用
    filepath = uploader.download_latest_version(downloads_dir, show_log=False)

    print(
        json.dumps(
            {
                "downloaded_path": filepath,
            }
        )
    )


if __name__ == "__main__":
    main()
