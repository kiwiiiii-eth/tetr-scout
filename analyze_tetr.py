#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import statistics
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


BASE_URL = "https://ch.tetr.io/api"
USER_AGENT = "tetr-cli-analyzer/0.2"
LANG_CHOICES = ("zh", "en", "both")

RESULT_LABELS = {
    1: "win",
    2: "loss",
    3: "dq_win",
    4: "dq_loss",
    5: "tie",
    6: "no_contest",
    7: "nullified",
}

WIN_CODES = {1, 3}
LOSS_CODES = {2, 4}
TIE_CODES = {5}
EFFECTIVE_CODES = WIN_CODES | LOSS_CODES | TIE_CODES
WEEKDAY_ZH = {
    "Monday": "星期一",
    "Tuesday": "星期二",
    "Wednesday": "星期三",
    "Thursday": "星期四",
    "Friday": "星期五",
    "Saturday": "星期六",
    "Sunday": "星期日",
}


@dataclass(frozen=True)
class Match:
    timestamp_raw: int
    played_at_utc: datetime
    result_code: int
    result_label: str
    tr_after: float
    opponent_tr: float

    @property
    def bucket(self) -> str | None:
        if self.result_code in WIN_CODES:
            return "W"
        if self.result_code in LOSS_CODES:
            return "L"
        if self.result_code in TIE_CODES:
            return "T"
        return None


@dataclass(frozen=True)
class RecentLeagueRecord:
    played_at_utc: datetime
    bucket: str | None
    result_label: str
    self_wins: int | None
    opponent_wins: int | None
    opponent_username: str | None
    self_pre_tr: float | None
    self_post_tr: float | None
    opponent_pre_tr: float | None
    apm: float | None
    pps: float | None
    vs: float | None
    round_buckets: tuple[str, ...]


def parse_records_limit_arg(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None

    try:
        parsed = int(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("records limit must be a non-negative integer or 'all' / --records-limit 必須是非負整數或 all") from exc

    if parsed < 0:
        raise argparse.ArgumentTypeError("records limit must be >= 0, or 'all' / --records-limit 必須 >= 0 或 all")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a TETR.IO player's TETRA LEAGUE performance. / 分析 TETR.IO 玩家在 TETRA LEAGUE 的戰績。"
    )
    parser.add_argument("username", help="TETR.IO username or user id / TETR.IO 使用者名稱或 user id")
    parser.add_argument(
        "--recent",
        type=int,
        default=20,
        help="recent match window to highlight (default: 20) / 要強調的近期場數視窗（預設 20）",
    )
    parser.add_argument(
        "--timezone",
        default="UTC",
        help="IANA timezone for display, e.g. Asia/Taipei (default: UTC) / 顯示用時區，例如 Asia/Taipei（預設 UTC）",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="optional path to export parsed leagueflow matches as CSV / 匯出 leagueflow 解析結果 CSV 的路徑",
    )
    parser.add_argument(
        "--records-limit",
        type=parse_records_limit_arg,
        default=100,
        help="league records to inspect for round-level resilience; use 0 to disable or all for full history (default: 100) / 要檢查的逐場 records 數量；0 為停用，all 為抓完整歷史（預設 100）",
    )
    parser.add_argument(
        "--html-report",
        nargs="?",
        const="__AUTO__",
        default=None,
        help="write a self-contained HTML report; optional path, default: output/<username>_report.html / 輸出獨立 HTML 報表；可選路徑，預設 output/<username>_report.html",
    )
    parser.add_argument(
        "--lang",
        choices=LANG_CHOICES,
        default="zh",
        help="output language: zh, en, or both (default: zh) / 輸出語言：zh、en、both（預設 zh）",
    )
    return parser


def parse_args() -> argparse.Namespace:
    return build_parser().parse_args()


def localized_text(lang: str, zh: str, en: str) -> str:
    if lang == "en":
        return en
    if lang == "both":
        return f"{zh} / {en}"
    return zh


def localized_weekday(name: str, lang: str) -> str:
    zh = WEEKDAY_ZH.get(name, name)
    return localized_text(lang, zh, name)


def html_lang_code(lang: str) -> str:
    return "en" if lang == "en" else "zh-Hant"


def request_json(path: str, session_id: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
    if query:
        path = f"{path}?{urlencode(query)}"

    request = Request(
        f"{BASE_URL}{path}",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Session-ID": session_id,
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"HTTP {exc.code} while requesting {path}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while requesting {path}: {exc.reason}") from exc

    if not payload.get("success"):
        error = payload.get("error") or {}
        raise RuntimeError(
            f"API request failed for {path}: {error.get('msg') or error or 'unknown error'}"
        )

    return payload


def is_millis(timestamp: int) -> bool:
    return timestamp >= 10_000_000_000


def to_datetime(timestamp: int) -> datetime:
    if is_millis(timestamp):
        return datetime.fromtimestamp(timestamp / 1000, tz=UTC)
    return datetime.fromtimestamp(timestamp, tz=UTC)


def parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def load_matches(leagueflow_payload: dict[str, Any]) -> list[Match]:
    raw = leagueflow_payload["data"]
    start = int(raw["startTime"])
    points = raw.get("points", [])

    matches: list[Match] = []
    for point in points:
        offset, result_code, tr_after, opponent_tr = point
        absolute_ts = start + int(offset)
        matches.append(
            Match(
                timestamp_raw=absolute_ts,
                played_at_utc=to_datetime(absolute_ts),
                result_code=int(result_code),
                result_label=RESULT_LABELS.get(int(result_code), f"unknown_{result_code}"),
                tr_after=float(tr_after),
                opponent_tr=float(opponent_tr),
            )
        )

    matches.sort(key=lambda match: match.timestamp_raw)
    return matches


def load_recent_league_records(
    records_payload: dict[str, Any] | None,
    owner_id: str | None,
) -> list[RecentLeagueRecord]:
    if not records_payload or not owner_id:
        return []

    entries = records_payload.get("data", {}).get("entries", [])
    records: list[RecentLeagueRecord] = []

    for entry in entries:
        results = entry.get("results", {})
        leaderboard = results.get("leaderboard") or []
        self_summary = next(
            (row for row in leaderboard if str(row.get("id")) == owner_id),
            None,
        )
        opponent_summary = next(
            (row for row in leaderboard if str(row.get("id")) != owner_id),
            None,
        )

        score_self = self_summary.get("wins") if isinstance(self_summary, dict) else None
        score_opponent = opponent_summary.get("wins") if isinstance(opponent_summary, dict) else None

        stats = self_summary.get("stats", {}) if isinstance(self_summary, dict) else {}
        extras = entry.get("extras", {})
        league_extras = extras.get("league", {})
        self_league = league_extras.get(owner_id)
        opponent_id = str(opponent_summary.get("id")) if isinstance(opponent_summary, dict) else None
        opponent_league = league_extras.get(opponent_id) if opponent_id else None

        round_buckets: list[str] = []
        for round_rows in results.get("rounds") or []:
            self_round = next((row for row in round_rows if str(row.get("id")) == owner_id), None)
            opponent_round = next((row for row in round_rows if str(row.get("id")) != owner_id), None)
            if not isinstance(self_round, dict) or not isinstance(opponent_round, dict):
                continue
            if self_round.get("alive") and not opponent_round.get("alive"):
                round_buckets.append("W")
            elif opponent_round.get("alive") and not self_round.get("alive"):
                round_buckets.append("L")

        result_label = str(extras.get("result") or "unknown")
        if result_label == "victory":
            bucket = "W"
        elif result_label == "defeat":
            bucket = "L"
        elif result_label == "draw":
            bucket = "T"
        else:
            bucket = None

        records.append(
            RecentLeagueRecord(
                played_at_utc=parse_iso_datetime(entry["ts"]),
                bucket=bucket,
                result_label=result_label,
                self_wins=int(score_self) if isinstance(score_self, int) else None,
                opponent_wins=int(score_opponent) if isinstance(score_opponent, int) else None,
                opponent_username=(
                    str(opponent_summary.get("username"))
                    if isinstance(opponent_summary, dict) and opponent_summary.get("username")
                    else None
                ),
                self_pre_tr=(
                    float(self_league[0]["tr"])
                    if isinstance(self_league, list) and len(self_league) >= 1 and self_league[0]
                    else None
                ),
                self_post_tr=(
                    float(self_league[1]["tr"])
                    if isinstance(self_league, list) and len(self_league) >= 2 and self_league[1]
                    else None
                ),
                opponent_pre_tr=(
                    float(opponent_league[0]["tr"])
                    if isinstance(opponent_league, list) and len(opponent_league) >= 1 and opponent_league[0]
                    else None
                ),
                apm=float(stats["apm"]) if isinstance(stats.get("apm"), (int, float)) else None,
                pps=float(stats["pps"]) if isinstance(stats.get("pps"), (int, float)) else None,
                vs=float(stats["vsscore"]) if isinstance(stats.get("vsscore"), (int, float)) else None,
                round_buckets=tuple(round_buckets),
            )
        )

    records.sort(key=lambda record: record.played_at_utc)
    return records


def build_prisecter(value: dict[str, Any]) -> str | None:
    pri = value.get("pri")
    sec = value.get("sec")
    ter = value.get("ter")
    if pri is None or sec is None or ter is None:
        return None
    return f"{pri}:{sec}:{ter}"


def fetch_league_records_history(
    username: str,
    session_id: str,
    records_limit: int | None,
) -> dict[str, Any] | None:
    if records_limit == 0:
        return None

    remaining = records_limit
    after: str | None = None
    merged_entries: list[dict[str, Any]] = []
    seen_entry_ids: set[str] = set()
    last_payload: dict[str, Any] | None = None

    while True:
        page_limit = 100 if remaining is None else min(100, remaining)
        query: dict[str, Any] = {"limit": page_limit}
        if after:
            query["after"] = after

        payload = request_json(f"/users/{username}/records/league/recent", session_id, query)
        last_payload = payload
        page_entries = payload.get("data", {}).get("entries", [])
        if not page_entries:
            break

        new_entries = []
        for entry in page_entries:
            entry_id = entry.get("_id") or entry.get("replayid")
            entry_id_str = str(entry_id) if entry_id is not None else None
            if entry_id_str and entry_id_str in seen_entry_ids:
                continue
            if entry_id_str:
                seen_entry_ids.add(entry_id_str)
            new_entries.append(entry)

        merged_entries.extend(new_entries)

        if remaining is not None:
            remaining -= len(new_entries)
            if remaining <= 0:
                break

        if len(page_entries) < page_limit:
            break

        last_cursor = build_prisecter(page_entries[-1].get("p", {}))
        if not last_cursor:
            break
        after = last_cursor

    if last_payload is None:
        return None

    merged_data = dict(last_payload.get("data", {}))
    merged_data["entries"] = merged_entries
    return {
        "success": True,
        "data": merged_data,
        "cache": last_payload.get("cache"),
    }


def format_number(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def format_optional(value: Any) -> str:
    if value in (None, "", -1):
        return "n/a"
    return str(value)


def format_percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "n/a"
    return f"{(numerator / denominator) * 100:.2f}%"


def format_signed(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.{digits}f}"


def format_rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.2f}%"


def compute_streak(values: list[str]) -> tuple[str | None, int]:
    if not values:
        return None, 0

    last = values[-1]
    count = 0
    for value in reversed(values):
        if value != last:
            break
        count += 1
    return last, count


def longest_run(values: list[str], target: str) -> int:
    best = 0
    current = 0
    for value in values:
        if value == target:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.fmean(values)


def win_rate_from_buckets(values: list[str | None]) -> float | None:
    resolved = [value for value in values if value in {"W", "L"}]
    if not resolved:
        return None
    return resolved.count("W") / len(resolved)


def count_runs(values: list[str], target: str, minimum: int) -> list[int]:
    runs: list[int] = []
    current = 0
    for value in values:
        if value == target:
            current += 1
        else:
            if current >= minimum:
                runs.append(current)
            current = 0
    if current >= minimum:
        runs.append(current)
    return runs


def summarize_window(matches: list[Match], size: int) -> dict[str, Any] | None:
    effective = [match for match in matches if match.bucket is not None]
    if not effective:
        return None

    window = effective[-size:]
    counts = Counter(match.bucket for match in window)
    last_match = window[-1]

    first_index = len(effective) - len(window)
    previous_tr = effective[first_index - 1].tr_after if first_index > 0 else None
    tr_delta = last_match.tr_after - previous_tr if previous_tr is not None else None

    return {
        "size": len(window),
        "wins": counts["W"],
        "losses": counts["L"],
        "ties": counts["T"],
        "win_rate": (counts["W"] / (counts["W"] + counts["L"])) if (counts["W"] + counts["L"]) else None,
        "avg_opponent_tr": average([match.opponent_tr for match in window]),
        "tr_delta": tr_delta,
        "form": "".join(match.bucket or "-" for match in window[-10:]),
    }


def find_peak_hour(matches: list[Match], tz: ZoneInfo) -> tuple[int, int] | None:
    effective = [match for match in matches if match.bucket is not None]
    if not effective:
        return None

    hours = Counter(match.played_at_utc.astimezone(tz).hour for match in effective)
    hour, count = hours.most_common(1)[0]
    return hour, count


def find_peak_weekday(matches: list[Match], tz: ZoneInfo) -> tuple[str, int] | None:
    effective = [match for match in matches if match.bucket is not None]
    if not effective:
        return None

    weekdays = Counter(match.played_at_utc.astimezone(tz).strftime("%A") for match in effective)
    return weekdays.most_common(1)[0]


def summarize_post_streak(
    effective: list[Match],
    target: str,
    streak_length: int,
    window_size: int = 3,
) -> dict[str, Any]:
    opportunities = 0
    next_match_results: list[str | None] = []
    next_window_results: list[str | None] = []
    run_length = 0

    for index, match in enumerate(effective):
        if match.bucket == target:
            run_length += 1
        else:
            run_length = 0

        if run_length == streak_length and index + 1 < len(effective):
            opportunities += 1
            next_match_results.append(effective[index + 1].bucket)
            next_window_results.extend(
                next_match.bucket for next_match in effective[index + 1 : index + 1 + window_size]
            )

    return {
        "samples": opportunities,
        "next_match_win_rate": win_rate_from_buckets(next_match_results),
        "next_window_win_rate": win_rate_from_buckets(next_window_results),
    }


def summarize_quick_requeue(
    effective: list[Match],
    fast_minutes: int = 10,
    cooldown_minutes: int = 30,
    max_minutes: int = 180,
) -> dict[str, dict[str, Any]]:
    groups = {
        "fast": {"results": [], "gaps": []},
        "cooldown": {"results": [], "gaps": []},
    }

    for index, match in enumerate(effective[:-1]):
        if match.bucket != "L":
            continue

        next_match = effective[index + 1]
        gap_minutes = (next_match.played_at_utc - match.played_at_utc).total_seconds() / 60
        if gap_minutes <= fast_minutes:
            group = "fast"
        elif cooldown_minutes <= gap_minutes <= max_minutes:
            group = "cooldown"
        else:
            continue

        groups[group]["results"].append(next_match.bucket)
        groups[group]["gaps"].append(gap_minutes)

    return {
        name: {
            "samples": len(group["results"]),
            "next_match_win_rate": win_rate_from_buckets(group["results"]),
            "avg_gap_minutes": average(group["gaps"]),
        }
        for name, group in groups.items()
    }


def split_sessions(effective: list[Match], break_minutes: int = 45) -> list[list[Match]]:
    if not effective:
        return []

    sessions: list[list[Match]] = [[effective[0]]]
    for match in effective[1:]:
        gap_minutes = (match.played_at_utc - sessions[-1][-1].played_at_utc).total_seconds() / 60
        if gap_minutes > break_minutes:
            sessions.append([match])
        else:
            sessions[-1].append(match)
    return sessions


def summarize_session_fatigue(
    effective: list[Match],
    break_minutes: int = 45,
    minimum_session_size: int = 6,
) -> dict[str, Any]:
    sessions = split_sessions(effective, break_minutes=break_minutes)
    qualified = [session for session in sessions if len(session) >= minimum_session_size]

    first_half_rates: list[float] = []
    second_half_rates: list[float] = []
    worse_second_half = 0
    avg_length = average([len(session) for session in qualified])

    for session in qualified:
        midpoint = len(session) // 2
        first_half = session[:midpoint]
        second_half = session[midpoint:]
        first_rate = win_rate_from_buckets([match.bucket for match in first_half])
        second_rate = win_rate_from_buckets([match.bucket for match in second_half])

        if first_rate is None or second_rate is None:
            continue

        first_half_rates.append(first_rate)
        second_half_rates.append(second_rate)
        if second_rate < first_rate:
            worse_second_half += 1

    return {
        "qualified_sessions": len(first_half_rates),
        "avg_session_length": avg_length,
        "first_half_win_rate": average(first_half_rates),
        "second_half_win_rate": average(second_half_rates),
        "worse_second_half": worse_second_half,
    }


def summarize_upset_loss_recovery(
    effective: list[Match],
    upset_threshold: float = 250,
    window_size: int = 3,
) -> dict[str, dict[str, Any]]:
    groups = {
        "upset": {"results": [], "windows": [], "gaps": []},
        "other": {"results": [], "windows": [], "gaps": []},
    }

    for index, match in enumerate(effective[:-1]):
        if match.bucket != "L":
            continue

        pre_tr = effective[index - 1].tr_after if index > 0 else None
        if pre_tr is None:
            continue

        opponent_gap = match.opponent_tr - pre_tr
        group = "upset" if opponent_gap <= -upset_threshold else "other"
        next_matches = effective[index + 1 : index + 1 + window_size]

        groups[group]["results"].append(effective[index + 1].bucket)
        groups[group]["windows"].extend(next_match.bucket for next_match in next_matches)
        groups[group]["gaps"].append(opponent_gap)

    return {
        name: {
            "samples": len(group["results"]),
            "next_match_win_rate": win_rate_from_buckets(group["results"]),
            "next_window_win_rate": win_rate_from_buckets(group["windows"]),
            "avg_opponent_gap": average(group["gaps"]),
        }
        for name, group in groups.items()
    }


def summarize_recent_resilience(records: list[RecentLeagueRecord]) -> dict[str, Any]:
    round1_lost: list[str | None] = []
    round1_won: list[str | None] = []
    zero_two_down: list[str | None] = []
    close_loss_next: list[str | None] = []
    blowout_loss_next: list[str | None] = []

    for index, record in enumerate(records):
        if record.round_buckets:
            if record.round_buckets[0] == "L":
                round1_lost.append(record.bucket)
            elif record.round_buckets[0] == "W":
                round1_won.append(record.bucket)

        if len(record.round_buckets) >= 2 and record.round_buckets[0] == "L" and record.round_buckets[1] == "L":
            zero_two_down.append(record.bucket)

        if index + 1 >= len(records) or record.bucket != "L":
            continue

        next_bucket = records[index + 1].bucket
        if record.self_wins == 2 and record.opponent_wins == 3:
            close_loss_next.append(next_bucket)
        elif (
            isinstance(record.self_wins, int)
            and isinstance(record.opponent_wins, int)
            and record.opponent_wins == 3
            and record.self_wins <= 1
        ):
            blowout_loss_next.append(next_bucket)

    return {
        "sample_size": len(records),
        "after_round1_loss_win_rate": win_rate_from_buckets(round1_lost),
        "after_round1_loss_samples": len(round1_lost),
        "after_round1_win_win_rate": win_rate_from_buckets(round1_won),
        "after_round1_win_samples": len(round1_won),
        "zero_two_comeback_rate": win_rate_from_buckets(zero_two_down),
        "zero_two_samples": len(zero_two_down),
        "close_loss_next_match_win_rate": win_rate_from_buckets(close_loss_next),
        "close_loss_samples": len(close_loss_next),
        "blowout_loss_next_match_win_rate": win_rate_from_buckets(blowout_loss_next),
        "blowout_loss_samples": len(blowout_loss_next),
    }


def build_analysis_snapshot(
    matches: list[Match],
    recent_records: list[RecentLeagueRecord],
    recent_size: int,
    tz: ZoneInfo,
) -> dict[str, Any]:
    effective = [match for match in matches if match.bucket is not None]
    effective_buckets = [match.bucket for match in effective if match.bucket is not None]
    counts = Counter(effective_buckets)
    current_streak_type, current_streak_size = compute_streak(effective_buckets)

    if current_streak_type == "W":
        streak_label = f"W{current_streak_size}"
    elif current_streak_type == "L":
        streak_label = f"L{current_streak_size}"
    elif current_streak_type == "T":
        streak_label = f"T{current_streak_size}"
    else:
        streak_label = "n/a"

    peak_hour = find_peak_hour(matches, tz)
    peak_weekday = find_peak_weekday(matches, tz)
    recent_sizes = []
    effective_count = len(effective)
    for candidate in (10, recent_size, 50):
        actual_size = min(candidate, effective_count)
        if actual_size > 0 and actual_size not in recent_sizes:
            recent_sizes.append(actual_size)

    recent_windows = {
        size: summarize_window(matches, size)
        for size in recent_sizes
    }

    slump_runs = count_runs(effective_buckets, "L", minimum=3)
    return {
        "effective": effective,
        "effective_buckets": effective_buckets,
        "counts": counts,
        "current_streak_label": streak_label,
        "best_win_streak": longest_run(effective_buckets, "W"),
        "best_loss_streak": longest_run(effective_buckets, "L"),
        "peak_hour": peak_hour,
        "peak_weekday": peak_weekday,
        "recent_sizes": recent_sizes,
        "recent_windows": recent_windows,
        "slump_runs": slump_runs,
        "post_loss_1": summarize_post_streak(effective, "L", 1),
        "post_loss_2": summarize_post_streak(effective, "L", 2),
        "post_loss_3": summarize_post_streak(effective, "L", 3),
        "quick_requeue": summarize_quick_requeue(effective),
        "fatigue": summarize_session_fatigue(effective),
        "upset_recovery": summarize_upset_loss_recovery(effective),
        "resilience": summarize_recent_resilience(recent_records),
    }


def maybe_path(value: str | None, username: str) -> Path | None:
    if value is None:
        return None
    if value == "__AUTO__":
        return Path("output") / f"{username}_report.html"
    return Path(value)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def downsample_series(points: list[tuple[datetime, float]], limit: int = 360) -> list[tuple[datetime, float]]:
    if len(points) <= limit:
        return points

    sampled: list[tuple[datetime, float]] = []
    last_index = len(points) - 1
    for index in range(limit):
        source_index = round(index * last_index / (limit - 1))
        sampled.append(points[source_index])
    return sampled


def build_loss_streak_bands(matches: list[Match], minimum: int = 3) -> list[tuple[datetime, datetime, int]]:
    effective = [match for match in matches if match.bucket is not None]
    bands: list[tuple[datetime, datetime, int]] = []
    run_start: int | None = None

    for index, match in enumerate(effective):
        if match.bucket == "L":
            if run_start is None:
                run_start = index
            continue

        if run_start is not None and index - run_start >= minimum:
            bands.append(
                (
                    effective[run_start].played_at_utc,
                    effective[index - 1].played_at_utc,
                    index - run_start,
                )
            )
        run_start = None

    if run_start is not None and len(effective) - run_start >= minimum:
        bands.append(
            (
                effective[run_start].played_at_utc,
                effective[-1].played_at_utc,
                len(effective) - run_start,
            )
        )

    return bands


def rolling_win_rate_series(matches: list[Match], window_size: int = 20) -> list[tuple[datetime, float]]:
    effective = [match for match in matches if match.bucket in {"W", "L"}]
    if len(effective) < window_size:
        return []

    points: list[tuple[datetime, float]] = []
    for index in range(window_size - 1, len(effective)):
        window = effective[index - window_size + 1 : index + 1]
        wins = sum(1 for match in window if match.bucket == "W")
        points.append((effective[index].played_at_utc, wins / window_size))
    return points


def svg_line_chart(
    points: list[tuple[datetime, float]],
    tz: ZoneInfo,
    title: str,
    y_label: str,
    color: str,
    y_min: float | None = None,
    y_max: float | None = None,
    bands: list[tuple[datetime, datetime, int]] | None = None,
    percent_mode: bool = False,
) -> str:
    if len(points) < 2:
        return "<div class='empty-state'>Not enough data for this chart.</div>"

    sampled = downsample_series(points)
    width = 960
    height = 320
    left = 64
    right = 20
    top = 18
    bottom = 38
    plot_width = width - left - right
    plot_height = height - top - bottom

    xs = [point[0].timestamp() for point in sampled]
    ys = [point[1] for point in sampled]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys) if y_min is None else y_min
    max_y = max(ys) if y_max is None else y_max
    if min_y == max_y:
        min_y -= 1
        max_y += 1

    def map_x(timestamp_value: float) -> float:
        if max_x == min_x:
            return left + plot_width / 2
        return left + ((timestamp_value - min_x) / (max_x - min_x)) * plot_width

    def map_y(y_value: float) -> float:
        return top + (1 - ((y_value - min_y) / (max_y - min_y))) * plot_height

    path_points = " ".join(
        f"{map_x(point[0].timestamp()):.2f},{map_y(point[1]):.2f}"
        for point in sampled
    )
    area_points = (
        f"{left:.2f},{top + plot_height:.2f} "
        + path_points
        + f" {left + plot_width:.2f},{top + plot_height:.2f}"
    )

    horizontal_grid = []
    for step in range(5):
        ratio = step / 4
        value = max_y - (max_y - min_y) * ratio
        y_coord = top + plot_height * ratio
        label = f"{value * 100:.0f}%" if percent_mode else f"{value:.0f}"
        horizontal_grid.append(
            f"<line x1='{left}' y1='{y_coord:.2f}' x2='{left + plot_width}' y2='{y_coord:.2f}' class='grid' />"
            f"<text x='{left - 10}' y='{y_coord + 4:.2f}' class='axis-label axis-label-right'>{html.escape(label)}</text>"
        )

    vertical_grid = []
    for step in range(5):
        ratio = step / 4
        timestamp_value = min_x + (max_x - min_x) * ratio
        x_coord = left + plot_width * ratio
        label = datetime.fromtimestamp(timestamp_value, tz=UTC).astimezone(tz).strftime("%Y-%m")
        vertical_grid.append(
            f"<line x1='{x_coord:.2f}' y1='{top}' x2='{x_coord:.2f}' y2='{top + plot_height}' class='grid grid-vertical' />"
            f"<text x='{x_coord:.2f}' y='{height - 12}' class='axis-label axis-center'>{html.escape(label)}</text>"
        )

    band_markup: list[str] = []
    for start_dt, end_dt, streak_size in bands or []:
        x1 = map_x(start_dt.timestamp())
        x2 = map_x(end_dt.timestamp())
        width_value = max(2.0, x2 - x1)
        band_markup.append(
            f"<rect x='{x1:.2f}' y='{top}' width='{width_value:.2f}' height='{plot_height:.2f}' class='slump-band' />"
            f"<text x='{x1 + width_value / 2:.2f}' y='{top + 16:.2f}' class='band-label axis-center'>L{streak_size}</text>"
        )

    return f"""
<figure class="panel">
  <figcaption class="chart-title">{html.escape(title)}</figcaption>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
    <text x="{left}" y="14" class="axis-label">{html.escape(y_label)}</text>
    {''.join(horizontal_grid)}
    {''.join(vertical_grid)}
    {''.join(band_markup)}
    <polygon points="{area_points}" class="area-fill" style="fill:{color};" />
    <polyline points="{path_points}" class="line-stroke" style="stroke:{color};" />
  </svg>
</figure>
""".strip()


def svg_bar_chart(
    items: list[tuple[str, float | None, str, str]],
    title: str,
    percent_mode: bool = True,
) -> str:
    valid_items = [item for item in items if item[1] is not None]
    if not valid_items:
        return "<div class='empty-state'>Not enough data for this chart.</div>"

    width = 960
    height = 320
    left = 54
    right = 18
    top = 20
    bottom = 88
    plot_width = width - left - right
    plot_height = height - top - bottom
    max_value = max(item[1] or 0 for item in valid_items)
    max_value = max(max_value, 1.0 if percent_mode else max_value)
    step_width = plot_width / len(valid_items)
    bar_width = min(90, step_width * 0.6)

    horizontal_grid = []
    for step in range(5):
        ratio = step / 4
        value = max_value * (1 - ratio)
        y_coord = top + plot_height * ratio
        label = f"{value * 100:.0f}%" if percent_mode else f"{value:.0f}"
        horizontal_grid.append(
            f"<line x1='{left}' y1='{y_coord:.2f}' x2='{left + plot_width}' y2='{y_coord:.2f}' class='grid' />"
            f"<text x='{left - 10}' y='{y_coord + 4:.2f}' class='axis-label axis-label-right'>{html.escape(label)}</text>"
        )

    bar_markup = []
    for index, (label, value, color, sample_label) in enumerate(valid_items):
        x_coord = left + step_width * index + (step_width - bar_width) / 2
        bar_height = 0 if value is None else (value / max_value) * plot_height
        y_coord = top + plot_height - bar_height
        value_label = "n/a" if value is None else (f"{value * 100:.1f}%" if percent_mode else f"{value:.1f}")
        text_x = x_coord + bar_width / 2
        bar_markup.append(
            f"<rect x='{x_coord:.2f}' y='{y_coord:.2f}' width='{bar_width:.2f}' height='{bar_height:.2f}' rx='8' class='bar' style='fill:{color};' />"
            f"<text x='{text_x:.2f}' y='{y_coord - 8:.2f}' class='bar-value axis-center'>{html.escape(value_label)}</text>"
            f"<text x='{text_x:.2f}' y='{height - 38:.2f}' class='axis-label axis-center'>{html.escape(label)}</text>"
            f"<text x='{text_x:.2f}' y='{height - 20:.2f}' class='axis-label axis-center muted'>{html.escape(sample_label)}</text>"
        )

    return f"""
<figure class="panel">
  <figcaption class="chart-title">{html.escape(title)}</figcaption>
  <svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">
    {''.join(horizontal_grid)}
    {''.join(bar_markup)}
  </svg>
</figure>
""".strip()


def build_takeaways(summary: dict[str, Any], snapshot: dict[str, Any], lang: str) -> list[str]:
    takeaways: list[str] = []
    resilience = snapshot["resilience"]
    upset_recovery = snapshot["upset_recovery"]
    fatigue = snapshot["fatigue"]
    recent20 = snapshot["recent_windows"].get(20) or snapshot["recent_windows"].get(min(snapshot["recent_windows"])) if snapshot["recent_windows"] else None

    if recent20 and recent20.get("win_rate") is not None:
        takeaways.append(
            localized_text(
                lang,
                "近期狀態強於生涯基準："
                f"最近 {recent20['size']} 場勝率 {format_rate(recent20['win_rate'])}，"
                f"高於生涯勝率 {format_percent(int(summary.get('gameswon', 0) or 0), int(summary.get('gamesplayed', 0) or 0))}。",
                "Recent form is stronger than lifetime baseline: "
                f"last {recent20['size']} win rate {format_rate(recent20['win_rate'])} vs lifetime {format_percent(int(summary.get('gameswon', 0) or 0), int(summary.get('gamesplayed', 0) or 0))}.",
            )
        )

    if resilience["after_round1_loss_win_rate"] is not None and resilience["after_round1_win_win_rate"] is not None:
        gap = resilience["after_round1_win_win_rate"] - resilience["after_round1_loss_win_rate"]
        takeaways.append(
            localized_text(
                lang,
                "開局影響很大："
                f"第 1 局輸掉後，整場勝率只有 {format_rate(resilience['after_round1_loss_win_rate'])}；"
                f"第 1 局拿下時則有 {format_rate(resilience['after_round1_win_win_rate'])}，"
                f"差距 {gap * 100:.1f} 個百分點。",
                "Opening rounds matter a lot: "
                f"after losing round 1, match win rate is {format_rate(resilience['after_round1_loss_win_rate'])}, "
                f"versus {format_rate(resilience['after_round1_win_win_rate'])} after winning round 1 "
                f"({gap * 100:.1f} pts gap).",
            )
        )

    if upset_recovery["upset"]["next_match_win_rate"] is not None and upset_recovery["other"]["next_match_win_rate"] is not None:
        takeaways.append(
            localized_text(
                lang,
                "爆冷輸球比一般敗場更傷："
                f"若輸給低自己至少 250 TR 的對手，下一場勝率會掉到 {format_rate(upset_recovery['upset']['next_match_win_rate'])}；"
                f"一般敗場後則是 {format_rate(upset_recovery['other']['next_match_win_rate'])}。",
                "Upset losses hurt more than normal losses: "
                f"next-match win rate drops to {format_rate(upset_recovery['upset']['next_match_win_rate'])} "
                f"after losing to an opponent at least 250 TR lower, compared with {format_rate(upset_recovery['other']['next_match_win_rate'])} after other losses.",
            )
        )

    if fatigue["first_half_win_rate"] is not None and fatigue["second_half_win_rate"] is not None:
        takeaways.append(
            localized_text(
                lang,
                "長 session 的疲勞存在，但不算嚴重："
                f"前半段勝率 {format_rate(fatigue['first_half_win_rate'])}，"
                f"後半段降到 {format_rate(fatigue['second_half_win_rate'])}。",
                "Session fatigue is present but mild: "
                f"qualified long sessions go from {format_rate(fatigue['first_half_win_rate'])} in the first half "
                f"to {format_rate(fatigue['second_half_win_rate'])} in the second half.",
            )
        )

    return takeaways[:4]


def write_html_report(
    path: Path,
    user_payload: dict[str, Any],
    summary_payload: dict[str, Any],
    matches: list[Match],
    recent_records: list[RecentLeagueRecord],
    snapshot: dict[str, Any],
    tz: ZoneInfo,
    lang: str,
) -> None:
    user = user_payload["data"]
    summary = summary_payload["data"]
    effective = snapshot["effective"]
    recent20 = snapshot["recent_windows"].get(20) or next(iter(snapshot["recent_windows"].values()), None)
    resilience = snapshot["resilience"]
    upset_recovery = snapshot["upset_recovery"]
    fatigue = snapshot["fatigue"]
    quick_requeue = snapshot["quick_requeue"]

    tr_points = [(match.played_at_utc, match.tr_after) for match in effective]
    rolling_points = rolling_win_rate_series(matches, window_size=20)
    loss_bands = build_loss_streak_bands(matches, minimum=3)

    tr_chart = svg_line_chart(
        points=tr_points,
        tz=tz,
        title=localized_text(lang, "TR 歷史曲線", "TR History Across Leagueflow"),
        y_label="TR",
        color="#1b6f53",
        bands=loss_bands,
    )
    rolling_chart = svg_line_chart(
        points=rolling_points,
        tz=tz,
        title=localized_text(lang, "20 場滾動勝率", "Rolling 20-Match Win Rate"),
        y_label=localized_text(lang, "勝率", "Win rate"),
        color="#c76b2f",
        y_min=0.0,
        y_max=1.0,
        percent_mode=True,
    )
    resilience_chart = svg_bar_chart(
        items=[
            (
                localized_text(lang, "第 1 局先輸", "R1 loss"),
                resilience["after_round1_loss_win_rate"],
                "#b85137",
                localized_text(lang, f"{resilience['after_round1_loss_samples']} 場", f"{resilience['after_round1_loss_samples']} matches"),
            ),
            (
                localized_text(lang, "第 1 局先贏", "R1 win"),
                resilience["after_round1_win_win_rate"],
                "#23745b",
                localized_text(lang, f"{resilience['after_round1_win_samples']} 場", f"{resilience['after_round1_win_samples']} matches"),
            ),
            (
                localized_text(lang, "0:2 落後翻盤", "0-2 comeback"),
                resilience["zero_two_comeback_rate"],
                "#d19c2f",
                localized_text(lang, f"{resilience['zero_two_samples']} 場", f"{resilience['zero_two_samples']} matches"),
            ),
            (
                localized_text(lang, "2:3 惜敗後", "After 2-3 loss"),
                resilience["close_loss_next_match_win_rate"],
                "#2f6fa8",
                localized_text(lang, f"{resilience['close_loss_samples']} 筆", f"{resilience['close_loss_samples']} samples"),
            ),
            (
                localized_text(lang, "0:3 或 1:3 後", "After 0-3 or 1-3"),
                resilience["blowout_loss_next_match_win_rate"],
                "#6f4f9b",
                localized_text(lang, f"{resilience['blowout_loss_samples']} 筆", f"{resilience['blowout_loss_samples']} samples"),
            ),
        ],
        title=localized_text(lang, "局級韌性", "Round-Level Resilience"),
    )
    recovery_chart = svg_bar_chart(
        items=[
            (
                localized_text(lang, "1 連敗後", "After 1L"),
                snapshot["post_loss_1"]["next_match_win_rate"],
                "#c76b2f",
                localized_text(lang, f"{snapshot['post_loss_1']['samples']} 筆", f"{snapshot['post_loss_1']['samples']} samples"),
            ),
            (
                localized_text(lang, "2 連敗後", "After 2L"),
                snapshot["post_loss_2"]["next_match_win_rate"],
                "#b85137",
                localized_text(lang, f"{snapshot['post_loss_2']['samples']} 筆", f"{snapshot['post_loss_2']['samples']} samples"),
            ),
            (
                localized_text(lang, "爆冷敗場後", "Upset loss"),
                upset_recovery["upset"]["next_match_win_rate"],
                "#8d4f2d",
                localized_text(lang, f"{upset_recovery['upset']['samples']} 筆", f"{upset_recovery['upset']['samples']} samples"),
            ),
            (
                localized_text(lang, "一般敗場後", "Other loss"),
                upset_recovery["other"]["next_match_win_rate"],
                "#23745b",
                localized_text(lang, f"{upset_recovery['other']['samples']} 筆", f"{upset_recovery['other']['samples']} samples"),
            ),
            (
                localized_text(lang, "快速重排", "Quick requeue"),
                quick_requeue["fast"]["next_match_win_rate"],
                "#3c7f99",
                localized_text(lang, f"{quick_requeue['fast']['samples']} 筆", f"{quick_requeue['fast']['samples']} samples"),
            ),
            (
                localized_text(lang, "冷卻後再排", "Cooldown"),
                quick_requeue["cooldown"]["next_match_win_rate"],
                "#6f8c3a",
                localized_text(lang, f"{quick_requeue['cooldown']['samples']} 筆", f"{quick_requeue['cooldown']['samples']} samples"),
            ),
        ],
        title=localized_text(lang, "輸球後恢復模式", "Recovery Patterns After Losses"),
    )
    fatigue_chart = svg_bar_chart(
        items=[
            (
                localized_text(lang, "Session 前半段", "Session first half"),
                fatigue["first_half_win_rate"],
                "#23745b",
                localized_text(lang, f"{fatigue['qualified_sessions']} 個 session", f"{fatigue['qualified_sessions']} sessions"),
            ),
            (
                localized_text(lang, "Session 後半段", "Session second half"),
                fatigue["second_half_win_rate"],
                "#c76b2f",
                localized_text(lang, f"{fatigue['qualified_sessions']} 個 session", f"{fatigue['qualified_sessions']} sessions"),
            ),
        ],
        title=localized_text(lang, "Session 疲勞", "Session Fatigue"),
    )

    takeaways = build_takeaways(summary, snapshot, lang)
    cards = [
        (
            localized_text(lang, "目前牌位", "Current rank"),
            format_optional(summary.get("rank")),
            localized_text(lang, "目前 TETRA LEAGUE 段位", "Current TETRA LEAGUE tier"),
        ),
        (
            localized_text(lang, "目前 TR", "Current TR"),
            format_number(summary.get("tr")),
            localized_text(lang, "目前 rating", "Current rating"),
        ),
        (
            localized_text(lang, "生涯勝率", "Lifetime WR"),
            format_percent(int(summary.get("gameswon", 0) or 0), int(summary.get("gamesplayed", 0) or 0)),
            localized_text(lang, f"{summary.get('gamesplayed', 'n/a')} 場官方對戰", f"{summary.get('gamesplayed', 'n/a')} official games"),
        ),
        (
            localized_text(lang, "近 20 場勝率", "Last 20 WR"),
            format_rate(recent20.get("win_rate") if recent20 else None),
            localized_text(
                lang,
                f"TR {format_signed(recent20.get('tr_delta') if recent20 else None, 0)}" if recent20 else "n/a",
                f"TR {format_signed(recent20.get('tr_delta') if recent20 else None, 0)}" if recent20 else "n/a",
            ),
        ),
        (
            localized_text(lang, "詳細紀錄", "Detailed records"),
            str(len(recent_records)),
            localized_text(lang, "可分頁逐場樣本", "Paginated match-detail samples"),
        ),
        (
            localized_text(lang, "目前連續紀錄", "Current streak"),
            snapshot["current_streak_label"],
            localized_text(lang, f"最佳 W{snapshot['best_win_streak']} / L{snapshot['best_loss_streak']}", f"Best W{snapshot['best_win_streak']} / L{snapshot['best_loss_streak']}"),
        ),
    ]

    card_markup = "".join(
        f"""
        <article class="card">
          <div class="card-label">{html.escape(label)}</div>
          <div class="card-value">{html.escape(value)}</div>
          <div class="card-note">{html.escape(note)}</div>
        </article>
        """.strip()
        for label, value, note in cards
    )

    takeaway_markup = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in takeaways
    )

    generated_at = datetime.now(tz=UTC).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S %Z")
    local_range = (
        f"{effective[0].played_at_utc.astimezone(tz).strftime('%Y-%m-%d')} to "
        f"{effective[-1].played_at_utc.astimezone(tz).strftime('%Y-%m-%d')}"
        if effective
        else localized_text(lang, "無資料", "n/a")
    )

    document = f"""<!DOCTYPE html>
<html lang="{html_lang_code(lang)}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(user.get('username', 'unknown'))} {html.escape(localized_text(lang, 'TETR.IO 報表', 'TETR.IO Report'))}</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --bg-accent: #e7dcc7;
      --surface: rgba(255, 250, 242, 0.86);
      --border: rgba(41, 36, 29, 0.12);
      --text: #201b16;
      --muted: #6c5f52;
      --ink-soft: rgba(32, 27, 22, 0.08);
      --green: #1b6f53;
      --orange: #c76b2f;
      --red: #b85137;
      --blue: #2f6fa8;
      --gold: #d19c2f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(209, 156, 47, 0.18), transparent 26%),
        radial-gradient(circle at top right, rgba(27, 111, 83, 0.16), transparent 28%),
        linear-gradient(180deg, var(--bg), #fbf7f0 56%, #efe6d7 100%);
    }}
    .page {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 32px 18px 56px;
    }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--border);
      border-radius: 28px;
      background:
        linear-gradient(135deg, rgba(255, 248, 237, 0.94), rgba(240, 232, 219, 0.88)),
        linear-gradient(180deg, rgba(255, 255, 255, 0.25), rgba(255, 255, 255, 0));
      box-shadow: 0 22px 60px rgba(50, 40, 28, 0.08);
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 12px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-family: "Avenir Next Condensed", "Arial Narrow", sans-serif;
      font-size: clamp(2.3rem, 5vw, 4.2rem);
      line-height: 0.95;
      letter-spacing: -0.04em;
    }}
    .subtitle {{
      max-width: 760px;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.6;
      margin: 0;
    }}
    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 14px;
      margin-top: 20px;
    }}
    .card, .panel, .note-panel {{
      border: 1px solid var(--border);
      background: var(--surface);
      backdrop-filter: blur(8px);
      box-shadow: 0 16px 40px rgba(50, 40, 28, 0.06);
    }}
    .card {{
      border-radius: 22px;
      padding: 18px;
    }}
    .card-label {{
      color: var(--muted);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin-bottom: 10px;
    }}
    .card-value {{
      font-size: 1.9rem;
      font-weight: 700;
      letter-spacing: -0.04em;
    }}
    .card-note {{
      margin-top: 8px;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .section-grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 16px;
      margin-top: 18px;
    }}
    .section-grid.single {{
      grid-template-columns: 1fr;
    }}
    .panel {{
      border-radius: 24px;
      padding: 18px 18px 8px;
      overflow: hidden;
    }}
    .note-panel {{
      border-radius: 24px;
      padding: 22px;
    }}
    .note-panel ul {{
      margin: 0;
      padding-left: 18px;
      line-height: 1.65;
    }}
    .chart-title {{
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 10px;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .grid {{
      stroke: var(--ink-soft);
      stroke-width: 1;
    }}
    .grid-vertical {{
      stroke-dasharray: 4 6;
    }}
    .line-stroke {{
      fill: none;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .area-fill {{
      opacity: 0.08;
    }}
    .slump-band {{
      fill: rgba(184, 81, 55, 0.09);
    }}
    .band-label {{
      fill: rgba(184, 81, 55, 0.78);
      font-size: 10px;
      font-weight: 700;
    }}
    .axis-label {{
      fill: var(--muted);
      font-size: 11px;
      font-family: "IBM Plex Sans", "Avenir Next", sans-serif;
    }}
    .axis-center {{
      text-anchor: middle;
    }}
    .axis-label-right {{
      text-anchor: end;
    }}
    .bar-value {{
      fill: var(--text);
      font-size: 11px;
      font-weight: 700;
      text-anchor: middle;
    }}
    .muted {{
      fill: var(--muted);
    }}
    .footer {{
      color: var(--muted);
      font-size: 0.9rem;
      margin-top: 18px;
      line-height: 1.7;
    }}
    .empty-state {{
      padding: 18px;
      color: var(--muted);
      border: 1px dashed var(--border);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.45);
    }}
    @media (max-width: 860px) {{
      .section-grid {{
        grid-template-columns: 1fr;
      }}
      .page {{
        padding: 16px 12px 28px;
      }}
      .hero {{
        padding: 22px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">{html.escape(localized_text(lang, 'TETR.IO 聯盟報表', 'TETR.IO League Report'))}</div>
      <h1>{html.escape(user.get('username', 'unknown'))}</h1>
      <p class="subtitle">
        {html.escape(localized_text(lang, '使用官方 TETRA CHANNEL API 端點建立的完整歷史報表。', 'Full-history report built from official TETRA CHANNEL API endpoints.'))}
        {html.escape(localized_text(lang, f'本地時區：{tz.key}。', f'Local timezone: {tz.key}.'))}
        {html.escape(localized_text(lang, f'歷史區間：{local_range}。', f'History range: {local_range}.'))}
        {html.escape(localized_text(lang, f'產生時間：{generated_at}。', f'Generated at {generated_at}.'))}
      </p>
      <div class="card-grid">{card_markup}</div>
    </section>

    <section class="section-grid">
      {tr_chart}
      <aside class="note-panel">
        <div class="chart-title">{html.escape(localized_text(lang, '重點觀察', 'What Stands Out'))}</div>
        <ul>{takeaway_markup}</ul>
      </aside>
    </section>

    <section class="section-grid single">
      {rolling_chart}
    </section>

    <section class="section-grid">
      {recovery_chart}
      {fatigue_chart}
    </section>

    <section class="section-grid single">
      {resilience_chart}
    </section>

    <p class="footer">
      {html.escape(localized_text(lang, '資料來源：', 'Data sources:'))}
      <code>/users/:user/summaries/league</code>, <code>/labs/leagueflow/:user</code>,
      {html.escape(localized_text(lang, '以及可分頁的', 'and paginated'))}
      <code>/users/:user/records/league/recent</code>。
      {html.escape(localized_text(lang, '由於官方端點的統計口徑不一定完全一致，詳細 records 的筆數可能和 summary 場數有些微差異。', 'The detailed-record count can differ slightly from summary games played because official endpoints do not always use exactly the same counting scope.'))}
    </p>
  </main>
</body>
</html>
"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")


def write_csv(path: Path, matches: list[Match], tz: ZoneInfo, lang: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                localized_text(lang, "對戰時間_UTC", "played_at_utc"),
                localized_text(lang, "對戰時間_本地", "played_at_local"),
                localized_text(lang, "結果", "result"),
                localized_text(lang, "桶位", "bucket"),
                localized_text(lang, "對戰後_TR", "tr_after"),
                localized_text(lang, "對手_TR", "opponent_tr"),
            ]
        )
        for match in matches:
            writer.writerow(
                [
                    match.played_at_utc.isoformat(),
                    match.played_at_utc.astimezone(tz).isoformat(),
                    match.result_label,
                    match.bucket or "",
                    f"{match.tr_after:.2f}",
                    f"{match.opponent_tr:.2f}",
                ]
            )


def safe_get_rank_benchmark(payload: dict[str, Any], rank: str) -> dict[str, Any] | None:
    labs = payload.get("data", {})
    rank_table = labs.get("data", {})
    if not isinstance(rank_table, dict):
        return None
    benchmark = rank_table.get(rank)
    if isinstance(benchmark, dict):
        return benchmark
    return None


def print_report(
    user_payload: dict[str, Any],
    summary_payload: dict[str, Any],
    ranks_payload: dict[str, Any] | None,
    matches: list[Match],
    recent_records: list[RecentLeagueRecord],
    snapshot: dict[str, Any],
    recent_size: int,
    tz: ZoneInfo,
    lang: str,
) -> None:
    user = user_payload["data"]
    summary = summary_payload["data"]
    effective = snapshot["effective"]
    counts = snapshot["counts"]
    peak_hour = snapshot["peak_hour"]
    peak_weekday = snapshot["peak_weekday"]
    recent_sizes = snapshot["recent_sizes"]
    slump_runs = snapshot["slump_runs"]
    post_loss_1 = snapshot["post_loss_1"]
    post_loss_2 = snapshot["post_loss_2"]
    post_loss_3 = snapshot["post_loss_3"]
    quick_requeue = snapshot["quick_requeue"]
    fatigue = snapshot["fatigue"]
    upset_recovery = snapshot["upset_recovery"]
    resilience = snapshot["resilience"]

    print(f"{localized_text(lang, '玩家', 'Player')}: {user.get('username', 'unknown')}")
    if user.get("country"):
        print(f"{localized_text(lang, '國家', 'Country')}: {user['country']}")
    print()

    print(localized_text(lang, "目前聯盟", "Current League"))
    print(
        "  " + localized_text(
            lang,
            "牌位: {rank}  |  TR: {tr}  |  排名: {standing}  |  百分位: {percentile} ({percentile_rank})".format(
                rank=format_optional(summary.get("rank")),
                tr=format_number(summary.get("tr")),
                standing=(
                    f"#{summary['standing']}"
                    if isinstance(summary.get("standing"), int) and summary["standing"] >= 0
                    else "n/a"
                ),
                percentile=(
                    f"{summary['percentile'] * 100:.2f}%"
                    if isinstance(summary.get("percentile"), (int, float))
                    else "n/a"
                ),
                percentile_rank=format_optional(summary.get("percentile_rank")),
            ),
            "Rank: {rank}  |  TR: {tr}  |  Standing: {standing}  |  Percentile: {percentile} ({percentile_rank})".format(
                rank=format_optional(summary.get("rank")),
                tr=format_number(summary.get("tr")),
                standing=(
                    f"#{summary['standing']}"
                    if isinstance(summary.get("standing"), int) and summary["standing"] >= 0
                    else "n/a"
                ),
                percentile=(
                    f"{summary['percentile'] * 100:.2f}%"
                    if isinstance(summary.get("percentile"), (int, float))
                    else "n/a"
                ),
                percentile_rank=format_optional(summary.get("percentile_rank")),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "Glicko: {glicko}  |  RD: {rd}  |  GXE: {gxe}".format(
                glicko=format_number(summary.get("glicko")),
                rd=format_number(summary.get("rd")),
                gxe=(f"{summary['gxe']:.2f}%" if isinstance(summary.get("gxe"), (int, float)) else "n/a"),
            ),
            "Glicko: {glicko}  |  RD: {rd}  |  GXE: {gxe}".format(
                glicko=format_number(summary.get("glicko")),
                rd=format_number(summary.get("rd")),
                gxe=(f"{summary['gxe']:.2f}%" if isinstance(summary.get("gxe"), (int, float)) else "n/a"),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "近期能力值: APM {apm}  |  PPS {pps}  |  VS {vs}".format(
                apm=format_number(summary.get("apm")),
                pps=format_number(summary.get("pps")),
                vs=format_number(summary.get("vs")),
            ),
            "Recent skill stats: APM {apm}  |  PPS {pps}  |  VS {vs}".format(
                apm=format_number(summary.get("apm")),
                pps=format_number(summary.get("pps")),
                vs=format_number(summary.get("vs")),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "升段路徑: 上一段 {prev_rank}  |  下一段 {next_rank}".format(
                prev_rank=format_optional(summary.get("prev_rank")),
                next_rank=format_optional(summary.get("next_rank")),
            ),
            "Promotion path: prev {prev_rank}  |  next {next_rank}".format(
                prev_rank=format_optional(summary.get("prev_rank")),
                next_rank=format_optional(summary.get("next_rank")),
            ),
        )
    )

    benchmark = safe_get_rank_benchmark(ranks_payload or {}, str(summary.get("rank", "")))
    if benchmark:
        print(
            "  " + localized_text(
                lang,
                "段位基準: 平均 APM {apm}, PPS {pps}, VS {vs}, 目標 TR {tr}".format(
                    apm=format_number(benchmark.get("apm")),
                    pps=format_number(benchmark.get("pps")),
                    vs=format_number(benchmark.get("vs")),
                    tr=format_number(benchmark.get("targettr")),
                ),
                "Rank benchmark: avg APM {apm}, PPS {pps}, VS {vs}, target TR {tr}".format(
                    apm=format_number(benchmark.get("apm")),
                    pps=format_number(benchmark.get("pps")),
                    vs=format_number(benchmark.get("vs")),
                    tr=format_number(benchmark.get("targettr")),
                ),
            )
        )

    print()
    print(localized_text(lang, "生涯數據", "Lifetime"))
    print(
        "  " + localized_text(
            lang,
            "總場數: {gamesplayed}  |  勝場: {gameswon}  |  勝率: {win_rate}".format(
                gamesplayed=summary.get("gamesplayed", "n/a"),
                gameswon=summary.get("gameswon", "n/a"),
                win_rate=format_percent(
                    int(summary.get("gameswon", 0) or 0),
                    int(summary.get("gamesplayed", 0) or 0),
                ),
            ),
            "Games: {gamesplayed}  |  Wins: {gameswon}  |  Win rate: {win_rate}".format(
                gamesplayed=summary.get("gamesplayed", "n/a"),
                gameswon=summary.get("gameswon", "n/a"),
                win_rate=format_percent(
                    int(summary.get("gameswon", 0) or 0),
                    int(summary.get("gamesplayed", 0) or 0),
                ),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "Leagueflow 解析場數: {matches}  |  有效比賽: {effective}".format(
                matches=len(matches),
                effective=len(effective),
            ),
            "Leagueflow parsed matches: {matches}  |  Effective matches: {effective}".format(
                matches=len(matches),
                effective=len(effective),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "解析結果: {wins}W {losses}L {ties}T  |  目前連續紀錄: {streak}  |  最佳連續紀錄: W{best_w} / L{best_l}".format(
                wins=counts["W"],
                losses=counts["L"],
                ties=counts["T"],
                streak=snapshot["current_streak_label"],
                best_w=snapshot["best_win_streak"],
                best_l=snapshot["best_loss_streak"],
            ),
            "Parsed results: {wins}W {losses}L {ties}T  |  Current streak: {streak}  |  Best streaks: W{best_w} / L{best_l}".format(
                wins=counts["W"],
                losses=counts["L"],
                ties=counts["T"],
                streak=snapshot["current_streak_label"],
                best_w=snapshot["best_win_streak"],
                best_l=snapshot["best_loss_streak"],
            ),
        )
    )

    if effective:
        print(
            "  " + localized_text(
                lang,
                "解析歷史中的 TR 範圍: {first} -> {last} ({delta})".format(
                    first=format_number(effective[0].tr_after),
                    last=format_number(effective[-1].tr_after),
                    delta=format_signed(effective[-1].tr_after - effective[0].tr_after, 0),
                ),
                "TR range in parsed history: {first} -> {last} ({delta})".format(
                    first=format_number(effective[0].tr_after),
                    last=format_number(effective[-1].tr_after),
                    delta=format_signed(effective[-1].tr_after - effective[0].tr_after, 0),
                ),
            )
        )

    print()
    print(localized_text(lang, "近期區段", "Recent Windows"))
    for size in recent_sizes:
        window = snapshot["recent_windows"].get(size)
        if not window:
            print("  " + localized_text(lang, f"最近 {size} 場: n/a", f"Last {size}: n/a"))
            continue
        win_rate = f"{window['win_rate'] * 100:.2f}%" if window["win_rate"] is not None else "n/a"
        print(
            "  " + localized_text(
                lang,
                "最近 {size} 場: {wins}W {losses}L {ties}T  |  勝率 {win_rate}  |  TR {tr_delta}  |  平均對手 TR {opp_tr}  |  近況 {form}".format(
                    size=window["size"],
                    wins=window["wins"],
                    losses=window["losses"],
                    ties=window["ties"],
                    win_rate=win_rate,
                    tr_delta=format_signed(window["tr_delta"], 0),
                    opp_tr=format_number(window["avg_opponent_tr"]),
                    form=window["form"],
                ),
                "Last {size}: {wins}W {losses}L {ties}T  |  Win rate {win_rate}  |  TR {tr_delta}  |  Avg opp TR {opp_tr}  |  Form {form}".format(
                    size=window["size"],
                    wins=window["wins"],
                    losses=window["losses"],
                    ties=window["ties"],
                    win_rate=win_rate,
                    tr_delta=format_signed(window["tr_delta"], 0),
                    opp_tr=format_number(window["avg_opponent_tr"]),
                    form=window["form"],
                ),
            )
        )

    if peak_weekday or peak_hour:
        print()
        print(localized_text(lang, "活躍模式", "Activity Pattern"))
        if peak_weekday:
            weekday, count = peak_weekday
            print("  " + localized_text(lang, f"最常玩的星期: {localized_weekday(weekday, lang)} ({count} 場)", f"Most active weekday: {weekday} ({count} matches)"))
        if peak_hour:
            hour, count = peak_hour
            print("  " + localized_text(lang, f"尖峰時段: {hour:02d}:00-{hour:02d}:59 {tz.key} ({count} 場)", f"Peak hour: {hour:02d}:00-{hour:02d}:59 {tz.key} ({count} matches)"))

    print()
    print(localized_text(lang, "Tilt / 低潮代理指標", "Tilt / Slump Proxies"))
    print(
        "  " + localized_text(
            lang,
            "出現過 3 連敗以上的次數: {count}  |  最長連敗群: L{longest}".format(
                count=len(slump_runs),
                longest=max(slump_runs) if slump_runs else 0,
            ),
            "3+ loss streaks observed: {count}  |  Longest loss cluster: L{longest}".format(
                count=len(slump_runs),
                longest=max(slump_runs) if slump_runs else 0,
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "輸 1 場後: 下一場勝率 {next_match} ({samples} 筆)  |  接下來 3 場勝率 {next_window}".format(
                next_match=format_rate(post_loss_1["next_match_win_rate"]),
                samples=post_loss_1["samples"],
                next_window=format_rate(post_loss_1["next_window_win_rate"]),
            ),
            "After 1 loss: next match WR {next_match} ({samples} samples)  |  next 3 matches WR {next_window}".format(
                next_match=format_rate(post_loss_1["next_match_win_rate"]),
                samples=post_loss_1["samples"],
                next_window=format_rate(post_loss_1["next_window_win_rate"]),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "2 連敗後: 下一場勝率 {next_match} ({samples} 筆)  |  接下來 3 場勝率 {next_window}".format(
                next_match=format_rate(post_loss_2["next_match_win_rate"]),
                samples=post_loss_2["samples"],
                next_window=format_rate(post_loss_2["next_window_win_rate"]),
            ),
            "After 2-loss streak: next match WR {next_match} ({samples} samples)  |  next 3 matches WR {next_window}".format(
                next_match=format_rate(post_loss_2["next_match_win_rate"]),
                samples=post_loss_2["samples"],
                next_window=format_rate(post_loss_2["next_window_win_rate"]),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "3 連敗後: 下一場勝率 {next_match} ({samples} 筆)  |  接下來 3 場勝率 {next_window}".format(
                next_match=format_rate(post_loss_3["next_match_win_rate"]),
                samples=post_loss_3["samples"],
                next_window=format_rate(post_loss_3["next_window_win_rate"]),
            ),
            "After 3-loss streak: next match WR {next_match} ({samples} samples)  |  next 3 matches WR {next_window}".format(
                next_match=format_rate(post_loss_3["next_match_win_rate"]),
                samples=post_loss_3["samples"],
                next_window=format_rate(post_loss_3["next_window_win_rate"]),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "輸球後快速重排 (<=10 分): 下一場勝率 {win_rate} ({samples} 筆，平均間隔 {gap} 分)".format(
                win_rate=format_rate(quick_requeue["fast"]["next_match_win_rate"]),
                samples=quick_requeue["fast"]["samples"],
                gap=format_number(quick_requeue["fast"]["avg_gap_minutes"], 1),
            ),
            "Quick requeue after loss (<=10m): next match WR {win_rate} ({samples} samples, avg gap {gap}m)".format(
                win_rate=format_rate(quick_requeue["fast"]["next_match_win_rate"]),
                samples=quick_requeue["fast"]["samples"],
                gap=format_number(quick_requeue["fast"]["avg_gap_minutes"], 1),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "輸球後冷卻再排 (30-180 分): 下一場勝率 {win_rate} ({samples} 筆，平均間隔 {gap} 分)".format(
                win_rate=format_rate(quick_requeue["cooldown"]["next_match_win_rate"]),
                samples=quick_requeue["cooldown"]["samples"],
                gap=format_number(quick_requeue["cooldown"]["avg_gap_minutes"], 1),
            ),
            "Cooldown after loss (30-180m): next match WR {win_rate} ({samples} samples, avg gap {gap}m)".format(
                win_rate=format_rate(quick_requeue["cooldown"]["next_match_win_rate"]),
                samples=quick_requeue["cooldown"]["samples"],
                gap=format_number(quick_requeue["cooldown"]["avg_gap_minutes"], 1),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "爆冷敗場後 (對手 <= 自己-250 TR): 下一場勝率 {next_match} ({samples} 筆)  |  接下來 3 場勝率 {next_window}".format(
                next_match=format_rate(upset_recovery["upset"]["next_match_win_rate"]),
                samples=upset_recovery["upset"]["samples"],
                next_window=format_rate(upset_recovery["upset"]["next_window_win_rate"]),
            ),
            "After upset losses (opp <= self-250 TR): next match WR {next_match} ({samples} samples)  |  next 3 matches WR {next_window}".format(
                next_match=format_rate(upset_recovery["upset"]["next_match_win_rate"]),
                samples=upset_recovery["upset"]["samples"],
                next_window=format_rate(upset_recovery["upset"]["next_window_win_rate"]),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "一般敗場後: 下一場勝率 {next_match} ({samples} 筆)  |  接下來 3 場勝率 {next_window}".format(
                next_match=format_rate(upset_recovery["other"]["next_match_win_rate"]),
                samples=upset_recovery["other"]["samples"],
                next_window=format_rate(upset_recovery["other"]["next_window_win_rate"]),
            ),
            "After other losses: next match WR {next_match} ({samples} samples)  |  next 3 matches WR {next_window}".format(
                next_match=format_rate(upset_recovery["other"]["next_match_win_rate"]),
                samples=upset_recovery["other"]["samples"],
                next_window=format_rate(upset_recovery["other"]["next_window_win_rate"]),
            ),
        )
    )

    print()
    print(localized_text(lang, "Session 疲勞", "Session Fatigue"))
    print(
        "  " + localized_text(
            lang,
            "Session >=6 場（間隔 >45 分視為新 session）: {count}  |  平均 session 長度 {length}".format(
                count=fatigue["qualified_sessions"],
                length=format_number(fatigue["avg_session_length"], 1),
            ),
            "Sessions >=6 matches (gap >45m starts new session): {count}  |  Avg session length {length}".format(
                count=fatigue["qualified_sessions"],
                length=format_number(fatigue["avg_session_length"], 1),
            ),
        )
    )
    print(
        "  " + localized_text(
            lang,
            "前半段勝率 {first}  |  後半段勝率 {second}  |  後半段更差的 session 數 {worse}".format(
                first=format_rate(fatigue["first_half_win_rate"]),
                second=format_rate(fatigue["second_half_win_rate"]),
                worse=fatigue["worse_second_half"],
            ),
            "First half WR {first}  |  Second half WR {second}  |  Worse second half in {worse} sessions".format(
                first=format_rate(fatigue["first_half_win_rate"]),
                second=format_rate(fatigue["second_half_win_rate"]),
                worse=fatigue["worse_second_half"],
            ),
        )
    )

    if recent_records:
        print()
        print(localized_text(lang, "詳細對戰韌性", "Detailed Match Resilience"))
        print(
            "  " + localized_text(
                lang,
                "檢查的詳細 records: {count}".format(
                    count=resilience["sample_size"],
                ),
                "Detailed records inspected: {count}".format(
                    count=resilience["sample_size"],
                ),
            )
        )
        print(
            "  " + localized_text(
                lang,
                "第 1 局先輸後: 整場勝率 {win_rate} ({samples} 場)".format(
                    win_rate=format_rate(resilience["after_round1_loss_win_rate"]),
                    samples=resilience["after_round1_loss_samples"],
                ),
                "After dropping round 1: match WR {win_rate} ({samples} matches)".format(
                    win_rate=format_rate(resilience["after_round1_loss_win_rate"]),
                    samples=resilience["after_round1_loss_samples"],
                ),
            )
        )
        print(
            "  " + localized_text(
                lang,
                "第 1 局先贏後: 整場勝率 {win_rate} ({samples} 場)".format(
                    win_rate=format_rate(resilience["after_round1_win_win_rate"]),
                    samples=resilience["after_round1_win_samples"],
                ),
                "After winning round 1: match WR {win_rate} ({samples} matches)".format(
                    win_rate=format_rate(resilience["after_round1_win_win_rate"]),
                    samples=resilience["after_round1_win_samples"],
                ),
            )
        )
        print(
            "  " + localized_text(
                lang,
                "從 0:2 落後開始: 翻盤率 {win_rate} ({samples} 場)".format(
                    win_rate=format_rate(resilience["zero_two_comeback_rate"]),
                    samples=resilience["zero_two_samples"],
                ),
                "From 0-2 down: comeback rate {win_rate} ({samples} matches)".format(
                    win_rate=format_rate(resilience["zero_two_comeback_rate"]),
                    samples=resilience["zero_two_samples"],
                ),
            )
        )
        print(
            "  " + localized_text(
                lang,
                "2:3 惜敗後的下一場: 勝率 {win_rate} ({samples} 筆)".format(
                    win_rate=format_rate(resilience["close_loss_next_match_win_rate"]),
                    samples=resilience["close_loss_samples"],
                ),
                "Next match after close 2-3 loss: WR {win_rate} ({samples} samples)".format(
                    win_rate=format_rate(resilience["close_loss_next_match_win_rate"]),
                    samples=resilience["close_loss_samples"],
                ),
            )
        )
        print(
            "  " + localized_text(
                lang,
                "0:3 / 1:3 較大比分輸掉後的下一場: 勝率 {win_rate} ({samples} 筆)".format(
                    win_rate=format_rate(resilience["blowout_loss_next_match_win_rate"]),
                    samples=resilience["blowout_loss_samples"],
                ),
                "Next match after 0-3 / 1-3 loss: WR {win_rate} ({samples} samples)".format(
                    win_rate=format_rate(resilience["blowout_loss_next_match_win_rate"]),
                    samples=resilience["blowout_loss_samples"],
                ),
            )
        )


def main() -> int:
    args = parse_args()
    try:
        tz = ZoneInfo(args.timezone)
    except Exception as exc:
        print(localized_text(args.lang, f"無效的時區: {args.timezone} ({exc})", f"Invalid timezone: {args.timezone} ({exc})"), file=sys.stderr)
        return 2

    session_id = f"tetr-cli-{uuid.uuid4()}"
    html_report_path = maybe_path(args.html_report, args.username)

    try:
        user_payload = request_json(f"/users/{args.username}", session_id)
        summary_payload = request_json(f"/users/{args.username}/summaries/league", session_id)
        leagueflow_payload = request_json(f"/labs/leagueflow/{args.username}", session_id)
        try:
            ranks_payload = request_json("/labs/league_ranks", session_id)
        except RuntimeError:
            ranks_payload = None
        try:
            records_payload = fetch_league_records_history(
                username=args.username,
                session_id=session_id,
                records_limit=args.records_limit,
            )
        except RuntimeError:
            records_payload = None
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    matches = load_matches(leagueflow_payload)
    recent_records = load_recent_league_records(records_payload, user_payload["data"].get("_id"))
    snapshot = build_analysis_snapshot(
        matches=matches,
        recent_records=recent_records,
        recent_size=max(1, args.recent),
        tz=tz,
    )
    print_report(
        user_payload=user_payload,
        summary_payload=summary_payload,
        ranks_payload=ranks_payload,
        matches=matches,
        recent_records=recent_records,
        snapshot=snapshot,
        recent_size=max(1, args.recent),
        tz=tz,
        lang=args.lang,
    )

    if args.csv:
        write_csv(args.csv, matches, tz, args.lang)
        print()
        print(localized_text(args.lang, f"CSV 已匯出至: {args.csv}", f"CSV exported to: {args.csv}"))

    if html_report_path:
        write_html_report(
            path=html_report_path,
            user_payload=user_payload,
            summary_payload=summary_payload,
            matches=matches,
            recent_records=recent_records,
            snapshot=snapshot,
            tz=tz,
            lang=args.lang,
        )
        print()
        print(localized_text(args.lang, f"HTML 報表已輸出至: {html_report_path}", f"HTML report written to: {html_report_path}"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
