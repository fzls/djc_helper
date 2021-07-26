# Google Analytics 4 上报脚本

import requests

from log import logger
from util import try_except, get_cid

# note: 查看数据地址 https://analytics.google.com/analytics/web/#/
# note: 当发现上报失败时，可以将打印的post body复制到 https://ga-dev-tools.web.app/ga4/event-builder/ 进行校验，看是否缺了参数，或者有参数不符合格式
# note: 参数文档 https://developers.google.com/analytics/devguides/collection/protocol/ga4/reference?client_type=gtag#payload_query_parameters
GA_API_BASE_URL = "https://www.google-analytics.com/mp/collect"
# GA_API_BASE_URL = "https://www.google-analytics.com/debug/mp/collect"
GA_API_SECRET = "Hyn3f-XnQIygfii6xju6Hg"
GA_MEASUREMENT_ID = "G-6C4M20MVJ4"

GA_API_URL = f"{GA_API_BASE_URL}?measurement_id={GA_MEASUREMENT_ID}&api_secret={GA_API_SECRET}"

headers = {
    "user-agent": "djc_helper",
}

common_data = {
    "client_id": get_cid(),
    "user_id": get_cid(),

    # 'v': '1',  # API Version.
    # 'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
    # 'cid': get_cid(),  # Anonymous Client Identifier. Ideally, this should be a UUID that is associated with particular user, device, or browser instance.
    # 'ua': 'djc_helper',
    #
    # 'an': "djc_helper",
    # 'av': now_version,
    #
    # 'ds': 'app',
    # 'sr': get_resolution(),
}


@try_except(show_exception_info=False)
def track_event(category: str, action: str, label=None, value=0, ga_misc_params: dict = None):
    if ga_misc_params is None:
        ga_misc_params = {}

    json_data = {
        **common_data,

        "events": [
            {
                "name": action,
                "params": {},
            }
        ],

        **ga_misc_params,  # 透传的一些额外参数
    }

    res = requests.post(GA_API_URL, json=json_data, headers=headers, timeout=10)
    logger.warning(f"request info: body = {res.request.body} res = {res.text}")


if __name__ == '__main__':
    track_event("ga4_example", "tutorial_begin")
