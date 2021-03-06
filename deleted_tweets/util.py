from datetime import datetime
import os

from dateutil import tz


def dt_from_timestampms(timestamp_ms):
    return datetime.utcfromtimestamp(int(timestamp_ms) / 1000)


def human_time_difference(origin_time, current_time=None):
    """
    https://stackoverflow.com/a/1551394/975018
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    if current_time is None:
        now = datetime.now()
    else:
        now = current_time

    diff = now - origin_time

    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return "after about " + str(second_diff) + " seconds"
        if second_diff < 120:
            return "after about a minute"
        if second_diff < 3600:
            return "after about " + str(int(second_diff / 60)) + " minutes"
        if second_diff < 7200:
            return "after about an hour"
        if second_diff < 86400:
            return "after about " + str(int(second_diff / 3600)) + " hours"
    if day_diff == 1:
        return "after at least yesterday"
    if day_diff < 7:
        return "after about " + str(day_diff) + " days"
    if day_diff < 31:
        return "after about " + str(int(day_diff / 7)) + " weeks"
    if day_diff < 365:
        return "after about " + str(int(day_diff / 30)) + " months"
    return "after about " + str(int(day_diff / 365)) + " years"


def short_human_time(origin_time, current_time=None):
    if current_time is None:
        now = datetime.now().astimezone(tz.UTC)
    else:
        now = current_time

    diff = now - origin_time

    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 60:
            return str(second_diff) + "s"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + "m"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + "h"
    if day_diff < 365:
        return origin_time.strftime('%b %d')
    return origin_time.strftime('%b %d, %Y')

def normalize_time_format_str(format_str):
    if os.name == 'nt':
        return format_str.replace('%-', '%#')
    return format_str
