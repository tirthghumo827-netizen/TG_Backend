from datetime import date, datetime, time, timedelta
WEEKDAY_SLOTS = [
    "19:30",
    "21:00"
]

WEEKEND_SLOTS = [
    "09:00",
    "10:30",
    "12:00",
    "13:30",
    "15:00",
    "16:30",
    "18:00",
    "19:30",
    "21:00"
]
FULL_SLOT_GRID = [
    "09:00",
    "10:30",
    "12:00",
    "13:30",
    "15:00",
    "16:30",
    "18:00",
    "19:30",
    "21:00"
]

# ---------------------------------------------------------------------------
# Raw Saarthi executive availability, transcribed from the weekly
# Shravan_Availability_Schedule.pdf shared over WhatsApp.
# Columns: (Exec1, Exec2, Exec3, Anurag)
# "-" = not available, "Whole Day" = fully available,
# "After X" = available from X onward, named entries (e.g. "Halali Trek") = blocked
# ---------------------------------------------------------------------------

RAW_SCHEDULE: dict[date, tuple[str, str, str, str]] = {
    date(2026, 7, 30): ("After 2:00 PM", "-", "-", "-"),
    date(2026, 7, 31): ("Whole Day", "-", "After 3:00 PM", "After 3:00 PM"),
    date(2026, 8, 1):  ("Whole Day", "-", "-", "Whole Day"),
    date(2026, 8, 2):  ("-", "-", "-", "-"),
    date(2026, 8, 3):  ("-", "-", "-", "-"),
    date(2026, 8, 4):  ("After 2:00 PM", "-", "-", "-"),
    date(2026, 8, 5):  ("Whole Day", "-", "After 3:00 PM", "After 3:00 PM"),
    date(2026, 8, 6):  ("-", "-", "-", "Whole Day"),
    date(2026, 8, 7):  ("-", "-", "-", "-"),
    date(2026, 8, 8):  ("After 2:00 PM", "-", "-", "-"),
    date(2026, 8, 9):  ("Whole Day", "Whole Day", "-", "-"),
    date(2026, 8, 10): ("Whole Day", "Whole Day", "After 3:00 PM", "After 3:00 PM"),
    date(2026, 8, 11): ("-", "Whole Day", "-", "Whole Day"),
    date(2026, 8, 12): ("-", "Whole Day", "-", "-"),
    date(2026, 8, 13): ("After 2:00 PM", "Whole Day", "-", "-"),
    date(2026, 8, 14): ("After 5:00 PM", "Whole Day", "After 3:00 PM", "After 3:00 PM"),
    date(2026, 8, 15): ("After 5:00 PM", "Whole Day", "Whole Day", "Whole Day"),
    date(2026, 8, 16): ("After 5:00 PM", "Whole Day", "-", "-"),
    date(2026, 8, 17): ("After 5:00 PM", "Whole Day", "-", "-"),
    date(2026, 8, 18): ("After 5:00 PM", "Whole Day", "-", "-"),
    date(2026, 8, 19): ("After 5:00 PM", "Whole Day", "-", "-"),
    date(2026, 8, 20): ("After 5:00 PM", "Whole Day", "After 3:00 PM", "After 3:00 PM"),
    date(2026, 8, 21): ("After 5:00 PM", "Whole Day", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 22): ("Halali Trek", "Halali Trek", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 23): ("Whole Day", "Whole Day", "Whole Day", "Whole Day"),
    date(2026, 8, 24): ("Whole Day", "Whole Day", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 25): ("Whole Day", "Whole Day", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 26): ("Whole Day", "Whole Day", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 27): ("Whole Day", "Whole Day", "After 5:00 PM", "After 5:00 PM"),
    date(2026, 8, 28): ("Whole Day", "Whole Day", "Whole Day", "Whole Day"),
}


def parse_availability(value: str | None):
    """
    None            -> not available
    "whole_day"     -> available all day
    datetime.time   -> available from this time onward
    """
    if not value:
        return None

    value = value.strip()

    if value in ("-", "—", ""):
        return None

    if value.lower() == "whole day":
        return "whole_day"

    if value.lower().startswith("after"):
        time_str = value[len("after"):].strip()
        return datetime.strptime(time_str, "%I:%M %p").time()

    # Anything else (e.g. "Halali Trek") = blocked
    return None


def get_day_level_slots(selected_date: date) -> list[str]:
    from .slots import FULL_SLOT_GRID  # adjust import path to match your layout

    raw_row = RAW_SCHEDULE.get(selected_date)
    if raw_row is None:
        return []

    parsed = [parse_availability(v) for v in raw_row]

    if "whole_day" in parsed:
        return FULL_SLOT_GRID

    available_from_times = [a for a in parsed if isinstance(a, time)]
    if not available_from_times:
        return []

    earliest_cutoff = min(available_from_times)

    return [
        slot for slot in FULL_SLOT_GRID
        if datetime.strptime(slot, "%H:%M").time() >= earliest_cutoff
    ]