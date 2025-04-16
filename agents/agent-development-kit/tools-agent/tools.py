from datetime import datetime
import pytz

def get_current_time(timezone_str: str):
    """
    Returns the current time in the given timezone.

    Args:
        timezone_str (str): The timezone string, e.g., 'Europe/Berlin', 'Asia/Tel_Aviv'

    Returns:
        str: The current time in ISO format.
    """
    try:
        tz = pytz.timezone(timezone_str)
        current_time = datetime.now(tz)
        return current_time.isoformat()
    except pytz.UnknownTimeZoneError:
        return f"Unknown timezone: {timezone_str}"
