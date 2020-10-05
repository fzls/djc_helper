# Google Analytics 上报脚本
import requests
import platform
import uuid

GA_TRACKING_ID = "UA-179595405-1"

def track_event(category, action, label=None, value=0):
    data = {
        'v': '1',  # API Version.
        'tid': GA_TRACKING_ID,  # Tracking ID / Property ID.
        # Anonymous Client Identifier. Ideally, this should be a UUID that is associated with particular user, device, or browser instance.
        'cid': get_cid(),
        't': 'event',  # Event hit type.
        'ec': category,  # Event category.
        'ea': action,  # Event action.
        'el': label,  # Event label.
        'ev': value,  # Event value, must be an integer
        'ua': 'requests'
    }

    response = requests.post(
        'https://www.google-analytics.com/collect', data=data)

def get_cid():
    return "{}-{}".format(platform.node(), uuid.getnode())

if __name__ == '__main__':
    track_event("example", "test")