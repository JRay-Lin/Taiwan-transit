# THSR Reference

Use `taiwan-transit hsr` for Taiwan High Speed Rail timetable lookup.

## CLI

```bash
cd skills/taiwan-transit
python3 -m scripts hsr --from 台北 --to 台中 --date 2025/01/15 --time 08:00 --json
python3 -m scripts hsr --from 台北 --to 台中
```

Use `python3 -m scripts ...`; this repository does not provide an executable wrapper.

## Parameters

| Parameter | Required | Default | Rule |
|---|---:|---|---|
| `--from` | Yes | None | Origin THSR station name. Accept `台` and `臺` variants where listed in Station Codes. Reject unknown stations. |
| `--to` | Yes | None | Destination THSR station name. Must be different from the origin for a useful query. |
| `--date` | No | Today in GMT+8 | Travel date. Accept `YYYY/MM/DD` or `YYYY-MM-DD`; normalize to `YYYY/MM/DD` before sending. |
| `--time` | No | Current time in GMT+8 | Earliest departure time in `HH:MM` 24-hour format. Returned trains earlier than this are filtered out locally. |
| `--json` | No | `false` | Print structured JSON instead of Traditional Chinese text. Use when another tool or agent will consume the output. |

## Station Codes

| Station | Code |
|---|---|
| 南港 | `NanGang` |
| 台北/臺北 | `TaiPei` |
| 板橋 | `BanQiao` |
| 桃園 | `TaoYuan` |
| 新竹 | `XinZhu` |
| 苗栗 | `MiaoLi` |
| 台中/臺中 | `TaiZhong` |
| 彰化 | `ZhangHua` |
| 雲林 | `YunLin` |
| 嘉義 | `JiaYi` |
| 台南/臺南 | `TaiNan` |
| 左營 | `ZuoYing` |

## Query Rules

- Official endpoint: `POST https://www.thsrc.com.tw/TimeTable/Search`
- Content type: `application/x-www-form-urlencoded`
- Normalize date as `YYYY/MM/DD` and time as `HH:MM`. If omitted, use the request-time date and time in GMT+8.
- Filter out returned trains whose `DepartureDate` differs from the requested `MM/DD`.
- Filter out returned trains earlier than the requested time.
- Sort remaining trains by `DepartureTime`.

## Result Meaning

Returned data is timetable information only. It does not prove seat availability, fare availability, live delay status, or completed booking.
