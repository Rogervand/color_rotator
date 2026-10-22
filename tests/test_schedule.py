"""Pure schedule logic tests."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from custom_components.color_rotator.schedule import evaluate

TZ = ZoneInfo("America/Detroit")


def sun(event, day):
    # sunrise 07:00, sunset 19:00 local, every day
    hour = 7 if event == "sunrise" else 19
    return datetime(day.year, day.month, day.day, hour, 0, tzinfo=TZ)


def sch(start, end, days=range(7), enabled=True):
    return {"enabled": enabled, "days": list(days), "start": start, "end": end}


T = lambda s: {"type": "time", "time": s, "offset": 0}  # noqa: E731


def at(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=TZ)


def test_disabled():
    st = evaluate(sch(T("18:00"), T("23:00"), enabled=False), at(2026, 10, 22, 20), TZ, sun)
    assert not st.active and st.next_event is None


def test_simple_window():
    s = sch(T("18:00"), T("23:00"))
    st = evaluate(s, at(2026, 10, 22, 12), TZ, sun)
    assert not st.active and st.next_is_start and st.next_event == at(2026, 10, 22, 18)
    st = evaluate(s, at(2026, 10, 22, 20), TZ, sun)
    assert st.active and st.next_event == at(2026, 10, 22, 23)
    st = evaluate(s, at(2026, 10, 22, 23, 30), TZ, sun)
    assert not st.active and st.next_event == at(2026, 10, 23, 18)


def test_overnight_window():
    s = sch(T("22:00"), T("02:00"))
    assert evaluate(s, at(2026, 10, 22, 23), TZ, sun).active
    st = evaluate(s, at(2026, 10, 23, 1), TZ, sun)  # started yesterday
    assert st.active and st.next_event == at(2026, 10, 23, 2)
    assert not evaluate(s, at(2026, 10, 23, 3), TZ, sun).active


def test_days_apply_to_start_day():
    # 2026-10-22 is a Thursday (3). Only Thursday allowed.
    s = sch(T("22:00"), T("02:00"), days=[3])
    assert evaluate(s, at(2026, 10, 23, 1), TZ, sun).active  # Fri 1am, started Thu
    st = evaluate(s, at(2026, 10, 23, 23), TZ, sun)  # Fri 11pm: not allowed
    assert not st.active and st.next_event == at(2026, 10, 29, 22)


def test_sun_with_offset():
    s = sch({"type": "sunset", "offset": -30}, {"type": "sunrise", "offset": 0})
    st = evaluate(s, at(2026, 10, 22, 18), TZ, sun)
    assert not st.active and st.next_event == at(2026, 10, 22, 18, 30)
    st = evaluate(s, at(2026, 10, 23, 3), TZ, sun)
    assert st.active and st.next_event == at(2026, 10, 23, 7)


def test_polar_no_sun():
    s = sch({"type": "sunset", "offset": 0}, T("23:00"))
    st = evaluate(s, at(2026, 10, 22, 12), TZ, lambda e, d: None)
    assert not st.active and st.next_event is None


def test_dst_fall_back():
    # US DST ends 2026-11-01 at 02:00
    s = sch(T("18:00"), T("23:00"))
    st = evaluate(s, at(2026, 10, 31, 23, 30), TZ, sun)
    assert st.next_event == datetime(2026, 11, 1, 18, 0, tzinfo=TZ)
    utc = ZoneInfo("UTC")
    elapsed = st.next_event.astimezone(utc) - at(2026, 10, 31, 23, 30).astimezone(utc)
    assert elapsed == timedelta(hours=19, minutes=30)  # extra hour from fall-back
