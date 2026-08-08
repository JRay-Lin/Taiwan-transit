from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO

from .cache import (
    DEFAULT_TRA_STATION_CACHE,
    TRA_STATION_CSV_URL,
    TransitError,
    update_tra_station_cache,
)
from .hsr import query_timetable as query_hsr_timetable
from .tra import query_timetable as query_tra_timetable


TAIWAN_TZ = timezone(timedelta(hours=8), "GMT+8")
TRA_END_OF_DAY = "23:59"


def load_default_cache_path() -> Path:
    return DEFAULT_TRA_STATION_CACHE


def main(
    argv: list[str] | None = None,
    *,
    opener=None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    now: datetime | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    parser = _build_parser()
    args = parser.parse_args(argv)
    request_now = _request_now(now)
    try:
        if args.command == "update":
            stations = update_tra_station_cache(
                opener=opener,
                cache_path=args.cache,
            )
            _emit(
                {"updated": len(stations), "stations": stations},
                f"已更新 TRA 車站快取：{len(stations)} 筆",
                json_output=args.json,
                stdout=stdout,
            )
            return 0
        if args.command == "hsr":
            results = query_hsr_timetable(
                args.origin,
                args.destination,
                _normalize_date(args.date, request_now),
                _normalize_time(args.time, request_now),
                opener=opener,
            )
            _emit_results("hsr", results, json_output=args.json, stdout=stdout)
            return 0
        if args.command == "tra":
            results = query_tra_timetable(
                args.origin,
                args.destination,
                _normalize_date(args.date, request_now),
                _normalize_time(args.time, request_now),
                TRA_END_OF_DAY,
                cache_path=args.cache,
                opener=opener,
                direct_only=args.direct_only,
            )
            _emit_results("tra", results, json_output=args.json, stdout=stdout)
            return 0
    except (TransitError, ValueError) as exc:
        print(str(exc), file=stderr)
        return 2
    parser.error("unknown command")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taiwan-transit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update = subparsers.add_parser("update", help="更新 TRA 車站快取")
    update.add_argument("--cache", help="TRA 車站快取 JSON 路徑")
    update.add_argument("--json", action="store_true", help="輸出 JSON")

    hsr = subparsers.add_parser("hsr", help="查詢高鐵時刻表")
    hsr.add_argument("--from", dest="origin", required=True, help="起站")
    hsr.add_argument("--to", dest="destination", required=True, help="迄站")
    hsr.add_argument("--date", help="日期，格式 YYYY/MM/DD 或 YYYY-MM-DD；預設為 GMT+8 今日")
    hsr.add_argument("--time", help="出發時間，格式 HH:MM；預設為 GMT+8 現在時間")
    hsr.add_argument("--json", action="store_true", help="輸出 JSON")

    tra = subparsers.add_parser("tra", help="查詢台鐵時刻表")
    tra.add_argument("--from", dest="origin", required=True, help="起站")
    tra.add_argument("--to", dest="destination", required=True, help="迄站")
    tra.add_argument("--date", help="日期，格式 YYYY/MM/DD 或 YYYY-MM-DD；預設為 GMT+8 今日")
    tra.add_argument("--time", help="最早出發時間，格式 HH:MM；預設為 GMT+8 現在時間")
    tra.add_argument("--direct-only", action="store_true", help="只查直達車")
    tra.add_argument("--cache", help="TRA 車站快取 JSON 路徑")
    tra.add_argument("--json", action="store_true", help="輸出 JSON")
    return parser


def _request_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(TAIWAN_TZ)
    if now.tzinfo is None:
        return now.replace(tzinfo=TAIWAN_TZ)
    return now.astimezone(TAIWAN_TZ)


def _normalize_date(value: str | None, request_now: datetime) -> str:
    if value is None:
        return request_now.strftime("%Y/%m/%d")
    normalized = value.strip().replace("-", "/")
    datetime.strptime(normalized, "%Y/%m/%d")
    return normalized


def _normalize_time(value: str | None, request_now: datetime) -> str:
    if value is None:
        return request_now.strftime("%H:%M")
    parsed = datetime.strptime(value.strip(), "%H:%M")
    return parsed.strftime("%H:%M")


def _emit(payload: dict, text: str, *, json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False), file=stdout)
    else:
        print(text, file=stdout)


def _emit_results(provider: str, results: list[dict], *, json_output: bool, stdout: TextIO) -> None:
    if json_output:
        print(json.dumps({"provider": provider, "results": results}, ensure_ascii=False), file=stdout)
        return
    if not results:
        print("查無符合條件的班次", file=stdout)
        return
    for result in results:
        if provider == "hsr":
            print(
                f"高鐵 {result['train_number']}：{result['departure_time']} → "
                f"{result['arrival_time']}，車程 {result['duration']}",
                file=stdout,
            )
        else:
            print(
                f"台鐵 {result['train_type']} {result['train_number']}："
                f"{result['departure_time']} → {result['arrival_time']}，"
                f"車程 {result['duration']}",
                file=stdout,
            )
