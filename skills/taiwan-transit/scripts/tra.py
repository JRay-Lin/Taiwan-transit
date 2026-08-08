from __future__ import annotations

import html
import re
from http.cookiejar import CookieJar
from html.parser import HTMLParser
from typing import Callable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from .cache import TRA_QUERY_URL, TransitError, load_tra_stations, resolve_tra_station


TRIP_ROW_RE = re.compile(
    r'<tr[^>]+class=["\'][^"\']*trip-column[^"\']*["\'][^>]*>(.*?)</tr>',
    re.I | re.S,
)


class CsrfParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.token: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        attr_map = {key: value or "" for key, value in attrs}
        if attr_map.get("name") == "_csrf" and attr_map.get("value"):
            self.token = html.unescape(attr_map["value"])


def _open(opener: Callable | None, request: Request):
    try:
        if opener is None:
            opener = _default_cookie_opener()
        return opener(request)
    except (OSError, TimeoutError, URLError) as exc:
        raise TransitError(f"官方站點請求失敗：{exc}") from exc


def _default_cookie_opener() -> Callable:
    cookie_opener = build_opener(HTTPCookieProcessor(CookieJar()))
    return lambda request: cookie_opener.open(request, timeout=30)


def query_timetable(
    origin: str,
    destination: str,
    date: str,
    start_time: str,
    end_time: str,
    *,
    cache_path=None,
    opener: Callable | None = None,
    direct_only: bool = False,
) -> list[dict[str, object]]:
    stations = load_tra_stations(cache_path)
    start = resolve_tra_station(origin, stations)
    end = resolve_tra_station(destination, stations)
    results = _query_once(
        start,
        end,
        date,
        start_time,
        end_time,
        "ONE",
        opener=opener,
    )
    if not results and not direct_only:
        results = _query_once(
            start,
            end,
            date,
            start_time,
            end_time,
            "NORMAL",
            opener=opener,
        )
    return sorted(results, key=lambda item: str(item["departure_time"]))


def _query_once(
    start: dict[str, str],
    end: dict[str, str],
    date: str,
    start_time: str,
    end_time: str,
    transfer: str,
    *,
    opener: Callable | None,
) -> list[dict[str, object]]:
    active_opener = opener or _default_cookie_opener()
    csrf = _fetch_csrf(active_opener)
    form = {
        "_csrf": csrf,
        "startStation": start["form_value"],
        "endStation": end["form_value"],
        "transfer": transfer,
        "rideDate": date,
        "startOrEndTime": "true",
        "startTime": start_time,
        "endTime": end_time,
        "trainTypeList": "ALL",
        "queryClassification": "NORMAL",
        "_trainEquipList": "on",
        "query": "查詢",
    }
    request = Request(
        TRA_QUERY_URL,
        data=urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with _open(active_opener, request) as response:
        response_html = response.read().decode("utf-8", errors="replace")
    return parse_itineraries(response_html, start["name"], end["name"])


def _fetch_csrf(opener: Callable | None) -> str:
    request = Request(TRA_QUERY_URL, method="GET")
    with _open(opener, request) as response:
        response_html = response.read().decode("utf-8", errors="replace")
    parser = CsrfParser()
    parser.feed(response_html)
    if parser.token is None:
        raise TransitError("台鐵查詢頁沒有找到 CSRF token")
    return parser.token


def parse_itineraries(response_html: str, origin: str, destination: str) -> list[dict[str, object]]:
    rows = TRIP_ROW_RE.findall(response_html)
    itineraries: list[dict[str, object]] = []
    for row in rows:
        train_number = _extract_cell(row, "train-number")
        if not train_number:
            continue
        train_type = _extract_cell(row, "train-type")
        departure_time = _extract_cell(row, "departure")
        arrival_time = _extract_cell(row, "arrival")
        duration = _extract_cell(row, "duration")
        itineraries.append(
            {
                "train_number": train_number,
                "train_type": train_type,
                "origin": origin,
                "destination": destination,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "duration": duration,
                "is_direct": True,
                "transfer_count": 0,
                "transfer_stations": [],
                "segments": [
                    {
                        "train_type": train_type,
                        "train_number": train_number,
                        "origin": origin,
                        "destination": destination,
                        "departure_time": departure_time,
                        "arrival_time": arrival_time,
                        "remarks": "",
                    }
                ],
                "remarks": [],
                "delay_info": None,
            }
        )
    return itineraries


def _extract_cell(row_html: str, class_name: str) -> str:
    pattern = re.compile(
        rf'<td[^>]+class=["\'][^"\']*{re.escape(class_name)}[^"\']*["\'][^>]*>(.*?)</td>',
        re.I | re.S,
    )
    match = pattern.search(row_html)
    if not match:
        return ""
    text = re.sub(r"<[^>]+>", "", match.group(1))
    return html.unescape(text).strip()
