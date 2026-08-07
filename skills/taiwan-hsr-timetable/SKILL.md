---
name: taiwan-hsr-timetable
description: "Use when querying Taiwan High Speed Rail (THSR) timetables."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [taiwan, thsr, high-speed-rail, timetable, transportation]
    related_skills: []
---

# Taiwan High Speed Rail Timetable

## Overview

Query the official Taiwan High Speed Rail (THSR) timetable endpoint and format the returned trains in Traditional Chinese. This endpoint is a timetable lookup only; it does **not** prove current seat availability or complete a reservation.

## When to Use

- The user asks for THSR trains between two Taiwan stations on a specified date/time.
- The user wants departure/arrival time, trip duration, non-reserved seating cars, or listed discounts.
- The user asks for an outbound trip and optionally supplies return date/time.

Do not use it for Taiwan Railways (TRA), metro, bus, or actual ticket booking.

## Required Inputs

Extract or ask for the following only when needed:

| Input | Required | Rule |
|---|---:|---|
| 起站 | Yes | Convert the Chinese station name to the official station code below. |
| 迄站 | Yes | Convert the Chinese station name to the official station code below. |
| 出發日期 | Yes | Format as `YYYY/MM/DD`. Resolve relative dates (e.g. 明天) from the live system date. |
| 出發時間 | Yes | Format as `HH:MM` (24-hour time). If the user says「8點之後」, use `08:00` and retain trains at or after that time. |
| 回程日期 | No | If omitted, send the outbound date. |
| 回程時間 | No | If omitted, send the outbound time. |

### Station-code mapping

| Station | Code |
|---|---|
| 南港 | `NanGang` |
| 台北 | `TaiPei` |
| 板橋 | `BanQiao` |
| 桃園 | `TaoYuan` |
| 新竹 | `XinZhu` |
| 苗栗 | `MiaoLi` |
| 台中 | `TaiZhong` |
| 彰化 | `ZhangHua` |
| 雲林 | `YunLin` |
| 嘉義 | `JiaYi` |
| 台南 | `TaiNan` |
| 左營 | `ZuoYing` |

Accept `臺` and `台` as equivalent in station names. Reject unknown stations rather than guessing.

## Official API Query

Use `POST https://www.thsrc.com.tw/TimeTable/Search` with `Content-Type: application/x-www-form-urlencoded`. Use `curl --data-urlencode` rather than manually percent-encoding dynamic inputs.

```bash
curl -sS --fail-with-body -X POST 'https://www.thsrc.com.tw/TimeTable/Search' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'SearchType=S' \
  --data-urlencode 'Lang=TW' \
  --data-urlencode 'StartStation=TaiZhong' \
  --data-urlencode 'EndStation=TaiPei' \
  --data-urlencode 'OutWardSearchDate=2026/08/07' \
  --data-urlencode 'OutWardSearchTime=08:00' \
  --data-urlencode 'ReturnSearchDate=2026/08/07' \
  --data-urlencode 'ReturnSearchTime=08:00' \
  --data-urlencode 'DiscountType=' \
  -o /tmp/thsr-timetable.json
```

Replace the four route/date/time values dynamically. Keep the remaining payload values unchanged unless the official endpoint changes.

## Parse and Filter Results

1. Parse JSON and verify `success` is true. Read `data.DepartureTable.Title` and `data.DepartureTable.TrainItem`.
2. The API may include a preceding-day overnight train and trains earlier than the requested time. Filter locally:
   - Exclude an item when `DepartureDate` is present and differs from the requested query date's `MM/DD`.
   - Retain only `DepartureTime >= 出發時間`.
   - Sort ascending by `DepartureTime`.
3. Retain the relevant fields for each `TrainItem`: `TrainNumber`, `DepartureTime`, `DestinationTime`, `Duration`, `NonReservedCar`, and `Discount`. Choose what to mention from them based on the user's question: a next-train query normally needs only the time, train number, arrival, and duration; include free-seat cars or discounts when requested or materially useful.
4. The endpoint can return many trains. For an open-ended query such as「8點後」, give the nearest useful options first and mention that more results exist when appropriate. Provide the complete filtered list only when the user asks for all trains.

Keep the filtered records available for answer composition; parsing code must not dictate a user-facing format.

## Presenting Results

Adapt the response to the user's actual question. Do not require a fixed heading, table, full field list, or stock closing sentence.

For a simple question such as「最近一班」, answer first in a natural, actionable sentence with the next departure, arrival, train number, and duration. Provide several trains only when the user requests alternatives or a time range. A table is optional and should be reserved for comparisons where it improves readability.

Describe the result as a timetable rather than seat availability when that distinction is relevant—for example, when the user asks about booking, remaining seats, fares, or real-time delay. Do not automatically attach a disclaimer to every timetable reply.

## Common Pitfalls

1. **Using the wrong station spelling/code.** `TaiPei` and `TaiZhong` use the endpoint's exact capitalization; do not substitute `Taipei` or `Taichung`.
2. **Trusting the raw first returned item.** The response can include an overnight train from the previous date, so apply the date filter.
3. **Assuming returned trains begin at the requested time.** Apply the local time filter before presenting results.
4. **Treating discounts as fare availability.** `Discount` is listed timetable eligibility; actual sale availability and price must be checked during booking.
5. **Treating timetable data as live inventory.** Clearly distinguish schedules from booking/seat availability.

## Verification Checklist

- [ ] Request used POST, form encoding, and the official endpoint.
- [ ] Route codes match the user’s stations.
- [ ] Date/time values were normalized to `YYYY/MM/DD` and `HH:MM`.
- [ ] API `success` was verified.
- [ ] Previous-day and earlier-than-requested trains were filtered out.
- [ ] Parsed records retain train number, departure, arrival, duration, free-seat, and discount data; the reply selects only what answers the user’s question.
- [ ] The response does not imply availability or a completed booking.
