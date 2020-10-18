# Google Analytics 上报脚本
import platform
import uuid
from urllib.parse import quote_plus

import requests

from log import logger
from version import now_version

GA_TRACKING_ID = "UA-179595405-1"


def track_event(category, action, label=None, value=0):
    try:
        data = {
            'v': '1',  # API Version.
            'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
            'cid': get_cid(),  # Anonymous Client Identifier. Ideally, this should be a UUID that is associated with particular user, device, or browser instance.
            'ua': 'requests',
            'av': now_version,

            't': 'event',  # Event hit type.
            'ec': category,  # Event category.
            'ea': action,  # Event action.
            'el': label,  # Event label.
            'ev': value,  # Event value, must be an integer
        }

        requests.post('https://www.google-analytics.com/collect', data=data, timeout=10)
    except BaseException as exc:
        logger.debug("track_event failed, category={}, action={}, label={}, value={} exc_info={}".format(category, action, label, value, exc))


def track_page(page):
    try:
        page = quote_plus(page)
        data = {
            'v': '1',  # API Version.
            'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
            'cid': get_cid(),  # Anonymous Client Identifier. Ideally, this should be a UUID that is associated with particular user, device, or browser instance.
            'ua': 'requests',
            'av': now_version,

            't': 'pageview',  # Event hit type.
            'dh': "djc-helper.com",  # Document hostname.
            'dp': page,  # Page.
            'dt': "",  # Title.
        }

        requests.post('https://www.google-analytics.com/collect', data=data, timeout=10)
    except BaseException as exc:
        logger.debug("track_page failed, page={} exc_info={}".format(page, exc))


def get_cid():
    return "{}-{}".format(platform.node(), uuid.getnode())


if __name__ == '__main__':
    # track_event("example", "test")
    track_page("/example/test_quote")
