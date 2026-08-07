---
name: taiwan-railway-timetable
description: "Use when querying Taiwan Railway (TRA) train timetables."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [taiwan, tra, railway, train, timetable, transportation]
    related_skills: [taiwan-hsr-timetable]
---

# Taiwan Railway Timetable

## Overview

Query the official Taiwan Railway (TRA) timetable form, retaining its session cookie and dynamically issued CSRF token. Resolve a station name to the required `車站代碼-車站名稱` form value, first search direct trains, then fall back to transfer itineraries only after a successful direct query has no results.

This is an itinerary/timetable lookup. It does not prove ticket inventory, complete booking, or guarantee real-time running status.

## When to Use

- The user asks for TRA/台鐵/臺鐵 trains between two stations on a date or within a time range.
- The user wants direct trains first, or is willing to accept transfer routes.
- The user asks for train number/type, departure/arrival, duration, transfer details, or remarks.

Do not use this skill for THSR, Taipei Metro, buses, or ticket purchase.

## Inputs and Normalization

Accept these inputs:

| Input | Required | Default / rules |
|---|---:|---|
| 起站 `startStation` | Yes | Accept a station name or an exact `code-name` value. Resolve names dynamically as below. |
| 迄站 `endStation` | Yes | Same rule as the origin. |
| 搭乘日期 `rideDate` | Yes | Normalize to `YYYY/MM/DD`. Resolve relative dates from the live system date. |
| 最早出發 `startTime` | No | `00:00`; format `HH:MM`. |
| 最晚出發 `endTime` | No | `23:59`; format `HH:MM`. |
| 是否只查直達車 | No | Always query direct first. If explicitly true, do **not** fall back to transfers. |
| 車種條件 | No | `ALL`, unless a verified official form value for a requested train type is supplied. |

Normalize common names before lookup:

```text
台北 → 臺北
台中 → 臺中
台南 → 臺南
台東 → 臺東
```

Do not guess incomplete or ambiguous station names. Ask the user to clarify instead.

## Station Resolution

The form requires values such as `1194-六家`, `1170-新豐`, `1000-臺北`, `3300-臺中`, `4220-臺南`, and `4400-高雄`. Never manually URL-encode these values or maintain a fragile flat text lookup.

For every query, fetch the official form first and parse station buttons structurally. The form exposes entries in this shape:

```html
<button class="btn tipStation" title="1194-六家">六家</button>
```

Create a mapping in memory such as:

```python
stations = {
  "六家": {"code": "1194", "name": "六家", "form_value": "1194-六家"},
  "新豐": {"code": "1170", "name": "新豐", "form_value": "1170-新豐"},
}
```

This captures the current official station data, including west coast, east coast, branch lines, and code changes. Use a real HTML parser when possible; a narrowly-scoped fallback regex is acceptable only for the stable `class="btn tipStation" title="code-name"` pattern. Validate that both requested stations resolve to exactly one official value.

## Session, CSRF, and Query Workflow

**Endpoint:** `https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytime`  
**Method:** `POST`  
**Content-Type:** `application/x-www-form-urlencoded`

1. Create a single cookie-aware HTTP session (`requests.Session()` if available, otherwise `urllib` + `HTTPCookieProcessor`).
2. `GET` the endpoint with that session. Do not reuse a CSRF token from any prior request.
3. Parse the latest hidden input `<input name="_csrf" value="...">`; retain the cookies returned by the GET.
4. Build raw form values and let the form encoder URL-encode them. Do not hand-build percent-encoded payload strings.
5. POST with the same session. Verify an HTTP-successful response is actually a valid results page, not an error page or an expired-token form.
6. Start with `transfer=ONE` (direct only). If — and only if — the response was successfully parsed and has **zero valid itineraries**, repeat the entire session/GET/CSRF/POST flow with `transfer=NORMAL`.
7. If the direct request fails due to network, HTTP, CSRF, or parse errors, retry or report the failure; **do not** misclassify it as no direct trains and fall back to transfers.

Use these fixed fields unless the live official form proves they have changed:

```text
startOrEndTime=true
trainTypeList=ALL
queryClassification=NORMAL
_trainEquipList=on
query=查詢
```

### Form payload

```python
payload = {
    "_csrf": csrf,
    "startStation": "1194-六家",     # dynamically resolved
    "endStation": "1170-新豐",       # dynamically resolved
    "transfer": "ONE",               # then NORMAL only after a verified no-result
    "rideDate": "2026/08/07",
    "startOrEndTime": "true",
    "startTime": "00:00",
    "endTime": "23:59",
    "trainTypeList": "ALL",
    "queryClassification": "NORMAL",
    "_trainEquipList": "on",
    "query": "查詢",
}
```

When using `curl`, use `--data-urlencode` for every dynamic form value. With `requests`, pass the raw `data=payload` dictionary. Repeated `_trainEquipList=on` fields are not needed initially: the official endpoint was tested successfully with one such field. If the form layout changes or the results differ, inspect the current form and reproduce its repeated fields as a list of `(key, value)` pairs.

## Result Validation and Parsing

The response is HTML. Parse the result table with class `itinerary-controls`, whose caption is `建議搭乘車次`.

### Distinguish outcomes

| Condition | Meaning | Action |
|---|---|---|
| HTTP/connection error, no CSRF, token error, malformed result page | Request failure | Retry once with a fresh GET/session; then report the error. Do not transfer-fallback. |
| A valid result table with `查無資料` and no itinerary | Valid no-result | With `ONE`, query `NORMAL`; with `NORMAL`, report no matching itinerary. |
| A valid result table with itinerary rows | Successful result | Parse, normalize, sort, and display it. |

### Required normalized result schema

For each itinerary return:

```json
{
  "train_number": "1701",
  "train_type": "區間",
  "origin": "六家",
  "destination": "新豐",
  "departure_time": "06:23",
  "arrival_time": "07:05",
  "duration": "00:42",
  "is_direct": false,
  "transfer_count": 1,
  "transfer_stations": ["新竹"],
  "segments": [
    {"train_type": "區間", "train_number": "1701", "origin": "六家", "destination": "新竹", "departure_time": "06:23", "arrival_time": "06:42", "remarks": "每日行駛。"},
    {"train_type": "區間", "train_number": "2114", "origin": "新竹", "destination": "新豐", "departure_time": "06:53", "arrival_time": "07:05", "remarks": "每日行駛。"}
  ],
  "remarks": [],
  "delay_info": null
}
```

Extract summary fields from the outer itinerary row and segment details from the nested/details table. Preserve remarks and any delay/status information the page actually supplies; never invent it. Mark an itinerary direct only when it has exactly one segment. For transfer routes, obtain `transfer_count` from segment count minus one, and transfer stations from the boundary between consecutive segments. Sort final itineraries by their first segment's departure time.

## Presenting Results

Adapt the response to the user's actual question; do not impose a fixed heading, table, field list, or stock closing sentence.

For a simple question such as「最近一班」, lead with one natural, actionable sentence containing the next departure time, arrival time, train type/number, and whether a transfer is needed. Add duration or a material caveat only when it helps the decision. For comparison, a requested time range, or transfer planning, give enough alternatives and details to support that choice; use a table only when it genuinely makes multiple options easier to compare.

State that the result is an official timetable and does not establish live running status or ticket availability only when this distinction is relevant, such as when the user asks about booking, seats, delays, or the information could otherwise be mistaken for them. Do not mechanically append this caveat to every response.

## Tested Behavior

The official endpoint was tested with the required GET → session cookie → dynamic CSRF → POST sequence. A single `_trainEquipList=on` field worked. For the example `六家 → 新豐`, `transfer=ONE` returned a valid `查無資料` result; `transfer=NORMAL` returned a valid one-transfer itinerary: 區間 1701 (六家→新竹), then 區間 2114 (新竹→新豐), with an 11-minute transfer. This confirms that no-result detection must be separate from request-failure handling.

## Common Pitfalls

1. **Hard-coding `_csrf`.** Tokens are session-bound and change. Always fetch a new form and use the same session for POST.
2. **Dropping cookies between GET and POST.** A valid-looking token can still fail without its session cookie.
3. **Using `臺北` without its code.** The server needs `1000-臺北`; dynamically resolve it before form encoding.
4. **Hand-encoding Chinese.** Pass raw Unicode form values to an encoder to prevent double encoding.
5. **Falling back to transfers after any error.** Only a successfully parsed no-result direct response permits `NORMAL` fallback.
6. **Equating no direct train with no journey.** Try `NORMAL` automatically unless the user requires direct travel only.
7. **Treating timetable results as inventory or live running information.** They are neither.

## Verification Checklist

- [ ] Both stations resolved uniquely to official `code-name` values.
- [ ] Date and times are normalized to `YYYY/MM/DD` and `HH:MM`.
- [ ] GET, cookie retention, and dynamic CSRF extraction occurred before each POST attempt.
- [ ] Form values were encoded by the HTTP client, not manually.
- [ ] Direct query outcome was validated before any transfer fallback.
- [ ] Parsed itineraries retain train type/number, stations, times, duration, direct/transfer status, segments, and page-provided remarks; the reply selects the information needed for the question.
- [ ] Results are sorted by departure time and do not imply booking availability.
