# THSR Reference

Use `taiwan-transit hsr` for Taiwan High Speed Rail timetable lookup.

## CLI

```bash
./skills/taiwan-transit/scripts/taiwan-transit hsr --from 台北 --to 台中 --date 2026/08/08 --time 08:00 --json
```

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
- Normalize date as `YYYY/MM/DD` and time as `HH:MM`.
- Filter out returned trains whose `DepartureDate` differs from the requested `MM/DD`.
- Filter out returned trains earlier than the requested time.
- Sort remaining trains by `DepartureTime`.

## Result Meaning

Returned data is timetable information only. It does not prove seat availability, fare availability, live delay status, or completed booking.
