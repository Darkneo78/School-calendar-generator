import json
from datetime import datetime, date, time
from pathlib import Path


DAY_MAP = {
    "MO": 0,
    "TU": 1,
    "WE": 2,
    "TH": 3,
    "FR": 4,
    "SA": 5,
    "SU": 6,
}


def parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def ics_escape(s: str) -> str:
    s = s or ""
    return (
        s.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def load_courses(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name} in {path.parent}")
    return json.loads(path.read_text(encoding="utf-8"))


def first_matching_date(term_start: date, term_end: date, days: list[str]) -> date | None:
    wanted = {DAY_MAP[d] for d in days}
    d = term_start
    while d <= term_end:
        if d.weekday() in wanted:
            return d
        d = d.fromordinal(d.toordinal() + 1)
    return None


def print_week_view(events: list[dict]) -> None:
    order = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
    print("\nWEEKLY VIEW")
    print("-" * 40)
    for d in order:
        items = [e for e in events if d in e["days"]]
        items.sort(key=lambda e: e["start"])
        print(f"\n{d}:")
        if not items:
            print("  (none)")
            continue
        for e in items:
            print(f"  {e['start']}–{e['end']}  {e['title']}")


def build_ics(term: str, term_start: date, term_end: date, events: list[dict]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//School Calendar Generator//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{ics_escape(term)}",
    ]

    until = datetime.combine(term_end, time(23, 59, 59)).strftime("%Y%m%dT%H%M%S")

    for e in events:
        title = e["title"]
        days = e["days"]
        start_t = parse_hhmm(e["start"])
        end_t = parse_hhmm(e["end"])
        location = e.get("location", "")
        notes = e.get("notes", "")

        first = first_matching_date(term_start, term_end, days)
        if first is None:
            continue

        dtstart = datetime.combine(first, start_t).strftime("%Y%m%dT%H%M%S")
        dtend = datetime.combine(first, end_t).strftime("%Y%m%dT%H%M%S")

        uid = f"{abs(hash((title, tuple(days), e['start'], e['end'], str(term_start), str(term_end))))}@school-calendar"

        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"SUMMARY:{ics_escape(title)}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"RRULE:FREQ=WEEKLY;BYDAY={','.join(days)};UNTIL={until}",
                f"LOCATION:{ics_escape(location)}",
                f"DESCRIPTION:{ics_escape(notes)}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> None:
    cfg = load_courses(Path("courses.json"))

    term = cfg["term"]
    term_start = date.fromisoformat(cfg["term_start"])
    term_end = date.fromisoformat(cfg["term_end"])
    events = cfg["events"]

    # quick validation to catch typos early
    for i, e in enumerate(events, start=1):
        if "title" not in e or "days" not in e or "start" not in e or "end" not in e:
            raise ValueError(f"Event #{i} is missing required keys (title/days/start/end).")
        for d in e["days"]:
            if d not in DAY_MAP:
                raise ValueError(f"Event #{i} has invalid day '{d}'. Use MO,TU,WE,TH,FR,SA,SU.")
        parse_hhmm(e["start"])
        parse_hhmm(e["end"])

    print_week_view(events)

    ics_text = build_ics(term, term_start, term_end, events)
    out_path = Path("school_calendar.ics")
    out_path.write_text(ics_text, encoding="utf-8")

    print(f"\n✅ Exported: {out_path.resolve()}")


if __name__ == "__main__":
    main()
