from __future__ import annotations

import json
from typing import Callable
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .cache import TransitError


THSR_QUERY_URL = "https://www.thsrc.com.tw/TimeTable/Search"

THSR_STATIONS = {
    "南港": "NanGang",
    "台北": "TaiPei",
    "臺北": "TaiPei",
    "板橋": "BanQiao",
    "桃園": "TaoYuan",
    "新竹": "XinZhu",
    "苗栗": "MiaoLi",
    "台中": "TaiZhong",
    "臺中": "TaiZhong",
    "彰化": "ZhangHua",
    "雲林": "YunLin",
    "嘉義": "JiaYi",
    "台南": "TaiNan",
    "臺南": "TaiNan",
    "左營": "ZuoYing",
}


def _open(opener: Callable | None, request: Request):
    try:
        if opener is None:
            return urlopen(request, timeout=30)
        return opener(request)
    except (OSError, TimeoutError, URLError) as exc:
        raise TransitError(f"官方站點請求失敗：{exc}") from exc


def query_timetable(
    origin: str,
    destination: str,
    date: str,
    time: str,
    *,
    opener: Callable | None = None,
) -> list[dict[str, str]]:
    start_code = _resolve_station_code(origin)
    end_code = _resolve_station_code(destination)
    form = {
        "SearchType": "S",
        "Lang": "TW",
        "StartStation": start_code,
        "EndStation": end_code,
        "OutWardSearchDate": date,
        "OutWardSearchTime": time,
        "ReturnSearchDate": date,
        "ReturnSearchTime": time,
        "DiscountType": "",
    }
    request = Request(
        THSR_QUERY_URL,
        data=urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with _open(opener, request) as response:
        try:
            payload = json.loads(response.read().decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise TransitError("高鐵時刻表回應不是有效 JSON") from exc
    if not payload.get("success"):
        raise TransitError("高鐵時刻表查詢失敗")
    items = payload.get("data", {}).get("DepartureTable", {}).get("TrainItem", [])
    requested_mmdd = "/".join(date.split("/")[1:])
    filtered = []
    for item in items:
        departure_date = item.get("DepartureDate")
        departure_time = item.get("DepartureTime", "")
        if departure_date and departure_date != requested_mmdd:
            continue
        if departure_time < time:
            continue
        filtered.append(
            {
                "train_number": item.get("TrainNumber", ""),
                "departure_time": departure_time,
                "arrival_time": item.get("DestinationTime", ""),
                "duration": item.get("Duration", ""),
                "non_reserved_car": item.get("NonReservedCar", ""),
                "discount": item.get("Discount", ""),
            }
        )
    return sorted(filtered, key=lambda item: item["departure_time"])


def _resolve_station_code(name: str) -> str:
    normalized = name.strip()
    try:
        return THSR_STATIONS[normalized]
    except KeyError as exc:
        raise TransitError(f"高鐵車站不支援：{name}") from exc
