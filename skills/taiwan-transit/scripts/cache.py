from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


TRA_QUERY_URL = "https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytime"
DEFAULT_TRA_STATION_CACHE = Path(__file__).with_name("data") / "tra_stations.json"


class TransitError(RuntimeError):
    """Raised for user-facing CLI errors."""


class StationButtonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stations: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "button":
            return
        attr_map = {key: value or "" for key, value in attrs}
        classes = set(attr_map.get("class", "").split())
        title = attr_map.get("title", "")
        if "tipStation" not in classes or "-" not in title:
            return
        code, name = title.split("-", 1)
        if code.isdigit() and name:
            self.stations.append({"code": code, "name": name, "aliases": _aliases_for(name)})


def _aliases_for(name: str) -> list[str]:
    aliases: list[str] = []
    if "臺" in name:
        aliases.append(name.replace("臺", "台"))
    if "台" in name:
        aliases.append(name.replace("台", "臺"))
    return aliases


def _open(opener: Callable | None, request: Request):
    try:
        if opener is None:
            return urlopen(request, timeout=30)
        return opener(request)
    except (OSError, TimeoutError, URLError) as exc:
        raise TransitError(f"官方站點請求失敗：{exc}") from exc


def load_tra_stations(cache_path: str | Path | None = None) -> list[dict[str, str]]:
    path = Path(cache_path) if cache_path is not None else DEFAULT_TRA_STATION_CACHE
    if not path.exists():
        raise TransitError(f"找不到 TRA 車站快取：{path}，請先執行 taiwan-transit update")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise TransitError(f"TRA 車站快取格式錯誤：{path}")
    stations: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict) or "code" not in item or "name" not in item:
            raise TransitError(f"TRA 車站快取格式錯誤：{path}")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list):
            aliases = []
        stations.append(
            {
                "code": str(item["code"]),
                "name": str(item["name"]),
                "aliases": [str(alias) for alias in aliases],
            }
        )
    return stations


def parse_tra_station_buttons(html: str) -> list[dict[str, str]]:
    parser = StationButtonParser()
    parser.feed(html)
    seen: set[tuple[str, str]] = set()
    stations: list[dict[str, str]] = []
    for station in parser.stations:
        key = (station["code"], station["name"])
        if key in seen:
            continue
        seen.add(key)
        stations.append(station)
    return stations


def update_tra_station_cache(
    *,
    opener: Callable | None = None,
    cache_path: str | Path | None = None,
) -> list[dict[str, str]]:
    request = Request(TRA_QUERY_URL, method="GET")
    with _open(opener, request) as response:
        html = response.read().decode("utf-8", errors="replace")
    stations = parse_tra_station_buttons(html)
    if not stations:
        raise TransitError("官方台鐵頁面沒有解析到車站資料")
    path = Path(cache_path) if cache_path is not None else DEFAULT_TRA_STATION_CACHE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return stations


def resolve_tra_station(name: str, stations: list[dict[str, str]]) -> dict[str, str]:
    normalized = name.strip()
    matches = [
        station
        for station in stations
        if normalized == station["name"] or normalized in station.get("aliases", [])
    ]
    if len(matches) == 1:
        station = matches[0]
        return {
            "code": station["code"],
            "name": station["name"],
            "form_value": f"{station['code']}-{station['name']}",
        }
    if not matches:
        raise TransitError(f"車站快取找不到：{name}，請先執行 taiwan-transit update")
    raise TransitError(f"車站名稱不唯一：{name}")
