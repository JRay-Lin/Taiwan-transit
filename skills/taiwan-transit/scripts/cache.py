from __future__ import annotations

import csv
import json
from pathlib import Path
from io import StringIO
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


TRA_QUERY_URL = "https://www.railway.gov.tw/tra-tip-web/tip/tip001/tip112/querybytime"
TRA_STATION_CSV_URL = (
    "https://quality.data.gov.tw/dq_download_csv.php?"
    "nid=33425&md5_url=82a54f59aa0559d7c4ef0aadb1ec1510"
)
DEFAULT_TRA_STATION_CACHE = Path(__file__).with_name("data") / "tra_stations.json"


class TransitError(RuntimeError):
    """Raised for user-facing CLI errors."""


def _aliases_for(name: str) -> list[str]:
    aliases: list[str] = []
    if "臺" in name:
        aliases.append(name.replace("臺", "台"))
    if "台" in name:
        aliases.append(name.replace("台", "臺"))
    return aliases


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


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


def parse_tra_station_csv(csv_text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")))
    seen: set[tuple[str, str]] = set()
    stations: list[dict[str, str]] = []
    for row in reader:
        code = _first_present(row, ["stationCode", "Station_Code4", "Station_Code3"])
        names = _dedupe(
            [
                _first_present(row, ["name", "網站中文站名"]),
                _first_present(row, ["stationName", "Station_Name"]),
            ]
        )
        if not code or not names:
            continue
        name = names[0]
        key = (code, name)
        if key in seen:
            continue
        seen.add(key)
        aliases = _dedupe([alias for alternate in names for alias in [alternate, *_aliases_for(alternate)]])
        aliases = [alias for alias in aliases if alias != name]
        stations.append({"code": code, "name": name, "aliases": aliases})
    return stations


def _first_present(row: dict[str, str | None], field_names: list[str]) -> str:
    for field_name in field_names:
        value = row.get(field_name)
        if value and value.strip():
            return value.strip()
    return ""


def update_tra_station_cache(
    *,
    opener: Callable | None = None,
    cache_path: str | Path | None = None,
) -> list[dict[str, str]]:
    request = Request(TRA_STATION_CSV_URL, method="GET")
    with _open(opener, request) as response:
        csv_text = response.read().decode("utf-8-sig", errors="replace")
    stations = parse_tra_station_csv(csv_text)
    if not stations:
        raise TransitError("政府公開資料 CSV 沒有解析到台鐵車站資料")
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
