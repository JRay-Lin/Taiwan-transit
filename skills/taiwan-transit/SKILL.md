---
name: taiwan-transit
description: Use when querying Taiwan public rail timetables, including THSR/high-speed rail, TRA/Taiwan Railway, 台鐵/臺鐵, 高鐵, train schedules, station normalization, or refreshing cached Taiwan Railway station data.
---

# Taiwan Transit

## Overview

Use the repository CLI to query Taiwan rail timetables. Prefer one integrated entry point, then choose `hsr`, `tra`, or `update` by the user's request.

## Quick Start

Run commands from the repository root:

```bash
cd skills/taiwan-transit
python3 -m scripts hsr --from 台北 --to 台中 --date 2025/01/15 --time 08:00
python3 -m scripts tra --from 六家 --to 新豐 --date 2025/01/15 --time 06:00
python3 -m scripts update
```

Use `python3 -m scripts ...`; this repository does not provide the previously documented executable wrapper. Add `--json` when another tool or agent needs structured output. For `hsr` and `tra`, omit `--date` to use today in GMT+8 and omit `--time` to use the request-time clock in GMT+8.

## Command Selection

| User intent | Command |
|---|---|
| 高鐵, THSR, Taiwan High Speed Rail | `taiwan-transit hsr` |
| 台鐵, 臺鐵, TRA, Taiwan Railway | `taiwan-transit tra` |
| TRA station not found, station cache stale, official station list changed | `taiwan-transit update` |

For HSR endpoint details, station codes, and filtering rules, read `references/hsr.md`.

For TRA cache rules, CSRF/session workflow, and result parsing, read `references/tra.md`.

## Cache Rule

TRA station names and codes are static cached data for normal queries. Do not fetch or infer TRA stations during `tra` lookup. If a station is missing or stale, run `taiwan-transit update` to refresh from the government open-data CSV, then retry the query.

## Common Mistakes

- Do not use `hsr` for 台鐵/TRA or `tra` for 高鐵/THSR.
- Do not treat timetable results as ticket inventory, live delay status, or booking confirmation.
- Do not manually percent-encode Chinese station names; the CLI handles form encoding.
- Do not edit the TRA station cache by hand unless the official update flow is unavailable and the source is verified.
