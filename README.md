# Taiwan Transit

Command-line timetable lookup for Taiwan High Speed Rail (THSR) and Taiwan Railway (TRA).

## Usage

Run from the repository root:

```bash
./skills/taiwan-transit/scripts/taiwan-transit hsr --from 台北 --to 台中 --date 2026/08/08 --time 08:00
./skills/taiwan-transit/scripts/taiwan-transit tra --from 六家 --to 新豐 --date 2026/08/08 --time 06:00
./skills/taiwan-transit/scripts/taiwan-transit update
```

For `hsr` and `tra`, `--date` defaults to today in GMT+8 and `--time` defaults to the request-time clock in GMT+8.

Use `--json` for structured output:

```bash
./skills/taiwan-transit/scripts/taiwan-transit hsr --from 台北 --to 台中 --date 2026/08/08 --time 08:00 --json
```

`cd skills/taiwan-transit && python3 -m scripts ...` works as an alternate entry point.

## TRA Station Cache

TRA station names and station codes are read from `skills/taiwan-transit/scripts/data/tra_stations.json`.
Normal `tra` queries do not fetch or update station data. Run `taiwan-transit update` when the station cache is missing or stale.

`update` refreshes the cache from the government open-data CSV for dataset 33425:

```text
https://quality.data.gov.tw/dq_download_csv.php?nid=33425&md5_url=82a54f59aa0559d7c4ef0aadb1ec1510
```

## Tests

```bash
python3 -m unittest tests.test_cli -v
```
