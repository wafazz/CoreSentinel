#!/usr/bin/env python3
"""
CoreSentinel Stats - Token usage & session analytics across all projects and tools.

Scans the session logs of whichever AI coding tools are installed (Claude Code,
Codex, Antigravity, Gemini CLI, ...) and reports per-project usage.

Usage:
    python agent-stats.py                  all detected tools
    python agent-stats.py --tool claude    one tool only
    python agent-stats.py --list           show which log dirs were found

Set MEMORYCORE_PATH to override where project-labels.json / the usage log live.
"""

import json
import os
import sys
import glob
from datetime import datetime
from collections import defaultdict, deque

MEMORY_PATH = os.environ.get("CORESENTINEL_PATH") or os.environ.get("MEMORYCORE_PATH") or os.path.dirname(os.path.abspath(__file__))
if MEMORY_PATH.startswith("{"):  # not rendered by setup - fall back to this file's folder
    MEMORY_PATH = os.path.dirname(os.path.abspath(__file__))

STATS_FILE = os.path.join(MEMORY_PATH, "agent-usage-log.json")
LABELS_FILE = os.path.join(MEMORY_PATH, "project-labels.json")

HOME = os.path.expanduser("~")

# Session-log locations per tool.
#   layout "dir-per-project": <root>/<project-key>/*.jsonl
#   layout "flat":            <root>/**/*.jsonl, project derived from the record
SOURCES = [
    {"key": "claude", "label": "Claude Code",
     "root": os.path.join(HOME, ".claude", "projects"), "layout": "dir-per-project"},
    {"key": "codex", "label": "OpenAI Codex",
     "root": os.path.join(HOME, ".codex", "sessions"), "layout": "flat"},
    {"key": "antigravity", "label": "Google Antigravity",
     "root": os.path.join(HOME, ".antigravity", "sessions"), "layout": "flat"},
    {"key": "gemini", "label": "Gemini CLI",
     "root": os.path.join(HOME, ".gemini", "tmp"), "layout": "dir-per-project"},
]

TOOL_CALL_MARKERS = ("tool_use", "function_call", "tool_call", "functioncall", "toolcall")


# ------------------------------------------------------------------- labels

def load_labels():
    if os.path.exists(LABELS_FILE):
        try:
            with open(LABELS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as err:
            sys.stderr.write(f"Warning loading labels: {err}\n")
    return {}


def save_labels(labels):
    try:
        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump(labels, f, indent=2)
    except OSError as err:
        sys.stderr.write(f"Warning saving labels: {err}\n")


def auto_label(dirname):
    name = dirname
    for sep in ("/", "\\"):
        home_key = HOME.replace(sep, "-")
        for prefix in (home_key + "-Desktop-", home_key + "-", "-" + home_key.lstrip("-") + "-"):
            if prefix and name.startswith(prefix):
                name = name[len(prefix):]
                break
    return name.replace("-", " ").replace("_", " ").strip().title() or dirname


def get_project_label(dirname, labels):
    if dirname in labels:
        return labels[dirname]
    label = auto_label(dirname)
    labels[dirname] = label
    save_labels(labels)
    return label


# -------------------------------------------------------------- log parsing

def first_usage(record):
    """Breadth-first search for the shallowest token-usage dict in a log record.

    Shapes differ per tool, and some tools also embed a cumulative total deeper
    in the record - taking only the shallowest hit avoids double counting.
    """
    queue = deque([(record, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth > 6:
            continue
        if isinstance(node, dict):
            if any(k in node for k in ("input_tokens", "prompt_tokens", "promptTokenCount")):
                return node
            for v in node.values():
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))
        elif isinstance(node, list):
            for v in node[:50]:
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))
    return None


def num(usage, *keys):
    for k in keys:
        v = usage.get(k)
        if isinstance(v, (int, float)):
            return int(v)
    return 0


def walk_blocks(record):
    """Yield every dict in the record that carries a 'type' or 'name' field."""
    queue = deque([(record, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth > 6:
            continue
        if isinstance(node, dict):
            yield node
            for v in node.values():
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))
        elif isinstance(node, list):
            for v in node[:200]:
                if isinstance(v, (dict, list)):
                    queue.append((v, depth + 1))


def parse_session(filepath):
    totals = {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
        "messages": 0, "tool_calls": 0, "user_messages": 0,
        "files_edited": set(), "files_read": set(),
        "cwd": None,
    }
    first_ts = None
    last_ts = None

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue

                ts = obj.get("timestamp") or obj.get("time") or obj.get("created_at")
                if isinstance(ts, str):
                    if first_ts is None:
                        first_ts = ts
                    last_ts = ts

                if totals["cwd"] is None:
                    cwd = obj.get("cwd") or obj.get("workspace") or obj.get("project")
                    if isinstance(cwd, str) and cwd:
                        totals["cwd"] = cwd

                role = obj.get("type") or obj.get("role")
                if role in ("user", "human"):
                    totals["messages"] += 1
                    totals["user_messages"] += 1
                elif role in ("assistant", "model"):
                    totals["messages"] += 1

                usage = first_usage(obj)
                if usage:
                    totals["input_tokens"] += num(usage, "input_tokens", "prompt_tokens", "promptTokenCount")
                    totals["output_tokens"] += num(usage, "output_tokens", "completion_tokens", "candidatesTokenCount")
                    totals["cache_read_input_tokens"] += num(
                        usage, "cache_read_input_tokens", "cached_input_tokens", "cachedContentTokenCount")
                    totals["cache_creation_input_tokens"] += num(usage, "cache_creation_input_tokens")

                for block in walk_blocks(obj):
                    btype = block.get("type")
                    if isinstance(btype, str) and btype.lower().replace("-", "_") in TOOL_CALL_MARKERS:
                        totals["tool_calls"] += 1
                        name = str(block.get("name") or "")
                        inp = block.get("input") or block.get("arguments") or block.get("args") or {}
                        if isinstance(inp, str):
                            try:
                                inp = json.loads(inp)
                            except ValueError:
                                inp = {}
                        if not isinstance(inp, dict):
                            continue
                        fp = inp.get("file_path") or inp.get("path") or inp.get("filePath") or ""
                        if not fp:
                            continue
                        low = name.lower()
                        if any(w in low for w in ("edit", "write", "replace", "apply_patch")):
                            totals["files_edited"].add(fp)
                        elif "read" in low or "view" in low:
                            totals["files_read"].add(fp)
    except (OSError, IOError) as err:
        totals["read_error"] = str(err)

    duration_min = 0
    if first_ts and last_ts:
        try:
            t1 = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            duration_min = max(0, int((t2 - t1).total_seconds() / 60))
        except ValueError:
            duration_min = 0

    return {
        **{k: v for k, v in totals.items() if k not in ("files_edited", "files_read")},
        "first_timestamp": first_ts, "last_timestamp": last_ts,
        "duration_min": duration_min,
        "files_edited_count": len(totals["files_edited"]),
        "files_read_count": len(totals["files_read"]),
        "files_edited_list": list(totals["files_edited"]),
    }


def blank_stats():
    return {
        "sessions": [], "total_input_tokens": 0, "total_output_tokens": 0,
        "total_cache_read": 0, "total_cache_creation": 0, "total_messages": 0,
        "total_tool_calls": 0, "total_files_edited": 0, "total_files_read": 0,
        "total_duration_min": 0, "session_count": 0, "hot_files": defaultdict(int),
    }


def accumulate(stats, sd):
    date = "unknown"
    if sd["first_timestamp"]:
        try:
            date = datetime.fromisoformat(
                sd["first_timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            date = "unknown"
    stats["sessions"].append({"date": date, "output_tokens": sd["output_tokens"]})
    stats["total_input_tokens"] += sd["input_tokens"]
    stats["total_output_tokens"] += sd["output_tokens"]
    stats["total_cache_read"] += sd["cache_read_input_tokens"]
    stats["total_cache_creation"] += sd["cache_creation_input_tokens"]
    stats["total_messages"] += sd["messages"]
    stats["total_tool_calls"] += sd["tool_calls"]
    stats["total_files_edited"] += sd["files_edited_count"]
    stats["total_files_read"] += sd["files_read_count"]
    stats["total_duration_min"] += sd["duration_min"]
    stats["session_count"] += 1
    for fp in sd["files_edited_list"]:
        stats["hot_files"][os.path.basename(fp.replace("\\", "/"))] += 1


def scan_source(source, labels):
    """Return {project_label: stats} for one tool, or {} if it isn't installed."""
    root = source["root"]
    results = {}
    if not os.path.isdir(root):
        return results

    if source["layout"] == "dir-per-project":
        for project_dir in sorted(os.listdir(root)):
            project_path = os.path.join(root, project_dir)
            if not os.path.isdir(project_path):
                continue
            label = get_project_label(project_dir, labels)
            stats = blank_stats()
            for log in glob.glob(os.path.join(project_path, "**", "*.jsonl"), recursive=True):
                sd = parse_session(log)
                if sd["messages"] == 0:
                    continue
                accumulate(stats, sd)
            if stats["session_count"]:
                results[label] = stats
    else:
        for log in glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True):
            sd = parse_session(log)
            if sd["messages"] == 0:
                continue
            key = sd["cwd"] or "Unlabelled"
            label = get_project_label(os.path.basename(key.rstrip("/\\")) or key, labels)
            stats = results.setdefault(label, blank_stats())
            accumulate(stats, sd)

    for stats in results.values():
        stats["hot_files"] = dict(sorted(stats["hot_files"].items(), key=lambda x: -x[1])[:5])
    return dict(sorted(results.items(), key=lambda x: -(
        x[1]["total_input_tokens"] + x[1]["total_output_tokens"]
        + x[1]["total_cache_read"] + x[1]["total_cache_creation"])))


def scan_all(only=None):
    labels = load_labels()
    out = []
    for source in SOURCES:
        if only and source["key"] not in only:
            continue
        results = scan_source(source, labels)
        if results:
            out.append((source["label"], results))
    return out


# ------------------------------------------------------------------ printing

def fmt(n):
    return f"{n:,}"


def dur(m):
    if m < 60:
        return f"{m}m"
    h, r = m // 60, m % 60
    return f"{h}h {r}m" if r else f"{h}h"


def print_stats(by_tool):
    grand = {"input": 0, "output": 0, "cr": 0, "cc": 0, "msg": 0, "tools": 0,
             "sess": 0, "fe": 0, "fr": 0, "dur": 0, "projects": 0}
    today = datetime.now().strftime("%Y-%m-%d")
    today_sess, today_tok = 0, 0

    print()
    print("=" * 62)
    print("  MemoryCore - Usage & Session Analytics")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    for tool_label, results in by_tool:
        print(f"\n  [{tool_label}]")
        for project, s in results.items():
            tt = (s["total_input_tokens"] + s["total_output_tokens"]
                  + s["total_cache_read"] + s["total_cache_creation"])
            avg_t = tt // s["session_count"]
            avg_d = s["total_duration_min"] // s["session_count"]
            print(f"\n  >> {project}")
            print(f"  {'-' * 50}")
            print(f"  Sessions        : {s['session_count']}")
            print(f"  Messages        : {fmt(s['total_messages'])}")
            print(f"  Tool Calls      : {fmt(s['total_tool_calls'])}")
            print(f"  Files Edited    : {fmt(s['total_files_edited'])}")
            print(f"  Files Read      : {fmt(s['total_files_read'])}")
            print(f"  Total Time      : {dur(s['total_duration_min'])}")
            print(f"  Avg/Session     : {fmt(avg_t)} tokens, {dur(avg_d)}")
            print(f"  Input Tokens    : {fmt(s['total_input_tokens'])}")
            print(f"  Output Tokens   : {fmt(s['total_output_tokens'])}")
            print(f"  Cache Read      : {fmt(s['total_cache_read'])}")
            print(f"  Cache Creation  : {fmt(s['total_cache_creation'])}")
            print(f"  Total Tokens    : {fmt(tt)}")
            if s["hot_files"]:
                hot = ", ".join(f"{f}({c})" for f, c in list(s["hot_files"].items())[:3])
                print(f"  Hot Files       : {hot}")
            for sess in s["sessions"]:
                if sess.get("date") == today:
                    today_sess += 1
                    today_tok += sess.get("output_tokens", 0)
            grand["input"] += s["total_input_tokens"]
            grand["output"] += s["total_output_tokens"]
            grand["cr"] += s["total_cache_read"]
            grand["cc"] += s["total_cache_creation"]
            grand["msg"] += s["total_messages"]
            grand["tools"] += s["total_tool_calls"]
            grand["sess"] += s["session_count"]
            grand["fe"] += s["total_files_edited"]
            grand["fr"] += s["total_files_read"]
            grand["dur"] += s["total_duration_min"]
            grand["projects"] += 1

    gt = grand["input"] + grand["output"] + grand["cr"] + grand["cc"]
    eff_ratio = gt // grand["fe"] if grand["fe"] else 0
    print(f"\n{'=' * 62}")
    print("  GRAND TOTAL & 9.0 OBSERVABILITY METRICS")
    print(f"  {'-' * 50}")
    print(f"  Tools           : {len(by_tool)}")
    print(f"  Projects        : {grand['projects']}")
    print(f"  Sessions        : {grand['sess']}")
    print(f"  Messages        : {fmt(grand['msg'])}")
    print(f"  Tool Calls      : {fmt(grand['tools'])}")
    print(f"  Files Edited    : {fmt(grand['fe'])}")
    print(f"  Files Read      : {fmt(grand['fr'])}")
    print(f"  Total Time      : {dur(grand['dur'])}")
    print(f"  Avg/Session     : {fmt(gt // grand['sess'] if grand['sess'] else 0)} tokens")
    print(f"  Token Efficiency: {fmt(eff_ratio)} tokens/edited file")
    print(f"  Total Tokens    : {fmt(gt)}")
    print("=" * 62)
    if today_sess:
        print(f"\n  TODAY ({today})")
        print(f"  {'-' * 50}")
        print(f"  Sessions        : {today_sess}")
        print(f"  Output Tokens   : {fmt(today_tok)}")
        print("=" * 62)
    print()

    log = {"timestamp": datetime.now().isoformat(), "grand_total": {
        "tools": len(by_tool), "projects": grand["projects"],
        "sessions": grand["sess"], "tokens": gt},
        "today": {"date": today, "sessions": today_sess}}
    history = []
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    if not isinstance(history, list):
        history = []
    history.append(log)
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except OSError as err:
        sys.stderr.write(f"Warning saving history: {err}\n")


def print_sources():
    print()
    print("  MemoryCore path:", MEMORY_PATH)
    print()
    for source in SOURCES:
        found = "found" if os.path.isdir(source["root"]) else "not installed"
        print(f"  {source['key']:<14} {source['label']:<20} {found:<14} {source['root']}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--list" in args:
        print_sources()
        sys.exit(0)
    only = None
    if "--tool" in args:
        i = args.index("--tool")
        if i + 1 < len(args):
            only = {t.strip() for t in args[i + 1].split(",") if t.strip()}
        else:
            print("\n  --tool needs a value, e.g. --tool claude,codex\n")
            sys.exit(1)
    data = scan_all(only)
    if data:
        print_stats(data)
    else:
        print("\n  No session data found. Run with --list to see which log folders were checked.\n")
