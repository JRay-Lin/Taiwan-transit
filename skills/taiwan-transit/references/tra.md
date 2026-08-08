# TRA Reference

Use `taiwan-transit tra` for Taiwan Railway timetable lookup.

## CLI

```bash
./skills/taiwan-transit/scripts/taiwan-transit tra --from 六家 --to 新豐 --date 2026/08/08 --time 06:00 --json
./skills/taiwan-transit/scripts/taiwan-transit tra --from 六家 --to 新豐
./skills/taiwan-transit/scripts/taiwan-transit update
```

## Parameters

### `tra`

| Parameter | Required | Default | Rule |
|---|---:|---|---|
| `--from` | Yes | None | Origin TRA station name. Resolve from the local station cache only; do not fetch station data during query. |
| `--to` | Yes | None | Destination TRA station name. Resolve from the local station cache only; do not guess unknown or ambiguous names. |
| `--date` | No | Today in GMT+8 | Travel date. Accept `YYYY/MM/DD` or `YYYY-MM-DD`; normalize to `YYYY/MM/DD` before sending. |
| `--time` | No | Current time in GMT+8 | Earliest departure time in `HH:MM` 24-hour format. The query window always ends at `23:59` for that date. |
| `--direct-only` | No | `false` | When present, query direct trains only and do not fall back to transfer itineraries. |
| `--cache` | No | `scripts/data/tra_stations.json` | Override the TRA station cache path. Useful for tests or temporary cache updates. |
| `--json` | No | `false` | Print structured JSON instead of Traditional Chinese text. Use when another tool or agent will consume the output. |

### `update`

| Parameter | Required | Default | Rule |
|---|---:|---|---|
| `--cache` | No | `scripts/data/tra_stations.json` | Destination cache path to overwrite after parsing the government open-data CSV. |
| `--json` | No | `false` | Print update count and station records as JSON instead of text. |

## Station Cache

TRA station names and codes are read from `skills/taiwan-transit/scripts/data/tra_stations.json` by default. Normal timetable queries must resolve stations from this cache before making any HTTP request.

Only `taiwan-transit update` fetches the government open-data station CSV and rewrites the station cache. If a station is missing, run update instead of parsing live station buttons during query.

Station cache update source:

```text
https://quality.data.gov.tw/dq_download_csv.php?nid=33425&md5_url=82a54f59aa0559d7c4ef0aadb1ec1510
```

Expected station CSV fields include `stationCode`, `stationName`, and `name`. Use `name` as the cache station name, with `stationName` as a fallback/alias.

## Query Workflow

Endpoint: `https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytime`

1. Load and resolve origin/destination from the local TRA station cache.
2. Create a cookie-aware session.
3. `GET` the endpoint and parse the current `_csrf` hidden input.
4. `POST` the form using the same session and raw Unicode station values like `1194-六家`.
5. Query direct trains first with `transfer=ONE`.
6. If the direct query returns a valid no-result page, retry with `transfer=NORMAL` unless `--direct-only` was supplied.

If `--date` or `--time` is omitted, use the request-time date and time in GMT+8. The CLI does not expose `--end-time`; it always submits `endTime=23:59`.

## Fixed Form Fields

```text
startOrEndTime=true
endTime=23:59
trainTypeList=ALL
queryClassification=NORMAL
_trainEquipList=on
query=查詢
```

## Result Meaning

Returned data is official timetable itinerary information only. It does not prove ticket inventory, live delay status, or completed booking.
