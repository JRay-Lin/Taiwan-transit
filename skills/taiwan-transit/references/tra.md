# TRA Reference

Use `taiwan-transit tra` for Taiwan Railway timetable lookup.

## CLI

```bash
./skills/taiwan-transit/scripts/taiwan-transit tra --from 六家 --to 新豐 --date 2026/08/08 --start-time 06:00 --end-time 09:00 --json
./skills/taiwan-transit/scripts/taiwan-transit update
```

## Station Cache

TRA station names and codes are read from `skills/taiwan-transit/data/tra_stations.json` by default. Normal timetable queries must resolve stations from this cache before making any HTTP request.

Only `taiwan-transit update` fetches the official form and rewrites the station cache. If a station is missing, run update instead of parsing live station buttons during query.

## Query Workflow

Endpoint: `https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytime`

1. Load and resolve origin/destination from the local TRA station cache.
2. Create a cookie-aware session.
3. `GET` the endpoint and parse the current `_csrf` hidden input.
4. `POST` the form using the same session and raw Unicode station values like `1194-六家`.
5. Query direct trains first with `transfer=ONE`.
6. If the direct query returns a valid no-result page, retry with `transfer=NORMAL` unless `--direct-only` was supplied.

## Fixed Form Fields

```text
startOrEndTime=true
trainTypeList=ALL
queryClassification=NORMAL
_trainEquipList=on
query=查詢
```

## Result Meaning

Returned data is official timetable itinerary information only. It does not prove ticket inventory, live delay status, or completed booking.
