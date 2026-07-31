"""Date parsing and formatting helpers shared by every module."""

from datetime import datetime

from .config import DATETIME_FORMAT, INPUT_DATE_FORMATS
from .exceptions import ValidationError


def now():
    """Current time at the precision the scheduler stores.

    Timestamps are persisted to the second, so truncating here keeps an
    in-memory task byte-identical to the same task reloaded from disk.
    """
    return datetime.now().replace(microsecond=0)


def parse_datetime(value, field="date"):
    """Parse ``value`` into a ``datetime`` truncated to whole seconds.

    Accepts ``datetime`` instances and strings in any of
    :data:`~task_scheduler.config.INPUT_DATE_FORMATS`. A bare date is
    interpreted as midnight of that day.

    Raises:
        ValidationError: if the value cannot be interpreted.
    """
    if isinstance(value, datetime):
        return value.replace(microsecond=0)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("{} must be a non-empty date string.".format(field.capitalize()))
    text = value.strip()
    for fmt in INPUT_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValidationError(
        "Could not read {} '{}'. Use YYYY-MM-DD or 'YYYY-MM-DD HH:MM'.".format(field, value)
    )


def coerce_datetime(value, field="date"):
    """Like :func:`parse_datetime` but maps empty input to ``None``."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return parse_datetime(value, field=field)


def format_datetime(value):
    """Render a ``datetime`` using the canonical format, or ``None``."""
    if value is None:
        return None
    return value.strftime(DATETIME_FORMAT)


def humanize_delta(target, reference=None):
    """Describe how far ``target`` is from ``reference`` in coarse, readable terms."""
    delta = target - (reference or now())
    seconds = int(abs(delta.total_seconds()))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60

    if days:
        amount = "{} day{}".format(days, "" if days == 1 else "s")
    elif hours:
        amount = "{} hour{}".format(hours, "" if hours == 1 else "s")
    else:
        amount = "{} minute{}".format(minutes, "" if minutes == 1 else "s")

    return "{} ago".format(amount) if delta.total_seconds() < 0 else "in {}".format(amount)
