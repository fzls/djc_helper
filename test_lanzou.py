from lanzou.api.utils import is_file_url, is_folder_url

#   1. 去下面这个查备案的网址查 鲁ICP备15001327号 ，看看是否有新的域名备案了
#       https://beian.miit.gov.cn/#/Integrated/recordQuery
all_lanzou_domains = [
    'lanzoup.com',  # 2021-12-10 鲁ICP备15001327号-16
    'lanzout.com',  # 2021-12-10 鲁ICP备15001327号-15
    'lanzouy.com',  # 2021-12-10 鲁ICP备15001327号-14
    'lanzoul.com',  # 2021-12-10 鲁ICP备15001327号-13
    'lanzoug.com',  # 2021-12-10 鲁ICP备15001327号-12
    'lanzouv.com',  # 2021-12-10 鲁ICP备15001327号-11
    'lanzouj.com',  # 2021-12-10 鲁ICP备15001327号-10
    'lanzouq.com',  # 2021-12-10 鲁ICP备15001327号-9
    'lanzouo.com',  # 2021-09-15 鲁ICP备15001327号-8
    'lanzouw.com',  # 2021-09-02 鲁ICP备15001327号-7
    'lanzoui.com',  # 2020-06-09 鲁ICP备15001327号-6
    'lanzoux.com',  # 2020-06-09 鲁ICP备15001327号-5
]


def test_is_file_url():
    # 确保每个备案的域名都能正确判定
    for domain in all_lanzou_domains:
        assert is_file_url(f'https://pan.{domain}/i1234abcd')


def test_is_folder_url():
    # 确保每个备案的域名都能正确判定
    for domain in all_lanzou_domains:
        assert is_folder_url(f'https://pan.{domain}/b1234abcd')
