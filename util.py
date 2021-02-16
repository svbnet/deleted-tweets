from datetime import datetime

def dt_from_timestampms(timestamp_ms):
    return datetime.fromtimestamp(int(timestamp_ms) / 1000)

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
            return str(second_diff) + " seconds"
        if second_diff < 120:
            return "a minute"
        if second_diff < 3600:
            return str(int(second_diff / 60)) + " minutes"
        if second_diff < 7200:
            return "an hour"
        if second_diff < 86400:
            return str(int(second_diff / 3600)) + " hours"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days"
    if day_diff < 31:
        return str(int(day_diff / 7)) + " weeks"
    if day_diff < 365:
        return str(int(day_diff / 30)) + " months"
    return str(int(day_diff / 365)) + " years"