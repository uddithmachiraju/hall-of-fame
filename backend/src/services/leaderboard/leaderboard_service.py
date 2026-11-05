from src.config.logging import get_logger
from src.schemas.leaderboards import BoardSpecification
from datetime import date, datetime, timedelta, timezone

logger = get_logger(__name__)


BUCKET_BITS = 22
SCORE_SHIFT = 1 << BUCKET_BITS
MAX_BUCKET = SCORE_SHIFT - 1
MAX_SCORE = (1 << 31) - 1

def build_leaderboard_specs(game_slug: str, now: datetime, region_code: str | None = None, game_epoch: datetime | None = None) -> list[BoardSpecification]:
    """Returns the applicable leaderboard keys and their metadata."""

    # Determine the period time based on the current date and the game's epoch.
    epoch = game_epoch or datetime(2026, 1, 1, tzinfo=timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start - timedelta(days=day_start.weekday())
    month_start = day_start.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    iso = week_start.isocalendar()

    # Define the leaderboard periods and their corresponding start and end times, as well as the resolution for each period.
    periods = [
        ("all_time", "all", epoch, None, 60),
        ("daily", day_start.strftime("%Y-%m-%d"), day_start, day_start + timedelta(days=1), 1),
        ("weekly", f"{iso.year}-W{iso.week:02d}", week_start, week_start + timedelta(days=7), 1),
        ("monthly", month_start.strftime("%Y-%m"), month_start, next_month, 1),
    ]

    scopes = [("global", "global")]
    if region_code:
        scopes.append(("regional", f"regional:{region_code}"))

    boards: list[BoardSpecification] = []

    # Generate leaderboard specifications for each combination of scope and period.
    for scope, scope_token in scopes:
        for period_time, label, start, end, resolution in periods:
            expire_at = int((now + timedelta(days=7)).timestamp())
            boards.append(
                BoardSpecification(
                    key=f"lb:{game_slug}:{scope_token}:{period_time}:{label}",
                    scope=scope,
                    period_type=period_time,
                    bucket=min(max(int((now - start).total_seconds() // resolution), 0), 2**31 - 1),
                    expire_at=expire_at,
                )
            )

    return boards
