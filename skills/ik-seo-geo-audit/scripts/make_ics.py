#!/usr/bin/env python3
"""make_ics.py — a recurring calendar reminder as an .ics file (for users without a calendar connector).

usage: make_ics.py --title "Quarterly SEO/GEO audit: example.com" --start 2027-01-12T10:00 --tz Europe/Kyiv \
                   --months 3 --description "Run /ik-seo-geo-audit ..." --out reminder.ics
"""
import argparse, uuid
from datetime import datetime, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--title", required=True); ap.add_argument("--start", required=True)
ap.add_argument("--tz", default="UTC"); ap.add_argument("--months", type=int, default=3)
ap.add_argument("--minutes", type=int, default=60); ap.add_argument("--description", default="")
ap.add_argument("--out", required=True)
a = ap.parse_args()
st = datetime.fromisoformat(a.start)
end_min = st.hour * 60 + st.minute + a.minutes
end = st.replace(hour=(end_min // 60) % 24, minute=end_min % 60)
fmt = "%Y%m%dT%H%M%S"
esc = lambda s: s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
ics = "\r\n".join([
    "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ik-seo-geo-audit//EN", "BEGIN:VEVENT",
    f"UID:{uuid.uuid4()}@ik-seo-geo-audit",
    f"DTSTAMP:{datetime.now(timezone.utc).strftime(fmt)}Z",
    f"DTSTART;TZID={a.tz}:{st.strftime(fmt)}", f"DTEND;TZID={a.tz}:{end.strftime(fmt)}",
    f"RRULE:FREQ=MONTHLY;INTERVAL={a.months}",
    f"SUMMARY:{esc(a.title)}", f"DESCRIPTION:{esc(a.description)}",
    "BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:-P1D", f"DESCRIPTION:{esc(a.title)}", "END:VALARM",
    "END:VEVENT", "END:VCALENDAR", ""])
open(a.out, "w", newline="").write(ics)
print("written", a.out)
