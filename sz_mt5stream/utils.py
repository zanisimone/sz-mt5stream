from datetime import datetime, timedelta
from .my_types import Timeframe


def get_next_candle_time(current_dt: datetime, timeframe: Timeframe) -> datetime:
    """Calculate when the next candle will close based on timeframe."""
    if timeframe == "M1":
        # Next minute boundary
        next_time = current_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    elif timeframe == "M5":
        # Next 5-minute boundary
        minute = ((current_dt.minute // 5) + 1) * 5
        if minute >= 60:
            next_time = (current_dt + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
        else:
            next_time = current_dt.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == "M15":
        # Next 15-minute boundary
        minute = ((current_dt.minute // 15) + 1) * 15
        if minute >= 60:
            next_time = (current_dt + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
        else:
            next_time = current_dt.replace(minute=minute, second=0, microsecond=0)
    elif timeframe == "H1":
        # Next hour boundary
        next_time = (current_dt + timedelta(hours=1)).replace(
            minute=0, second=0, microsecond=0
        )
    elif timeframe == "D1":
        # Next day boundary
        next_time = (current_dt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    return next_time
