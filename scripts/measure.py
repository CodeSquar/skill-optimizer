#!/usr/bin/env python3
"""What a Claude Code run cost, from its transcript, in one call.

  python measure.py TRANSCRIPT.jsonl|PROJECT_DIR [--turn N] [--from ISO] [--to ISO] [--top 12]

PROJECT_DIR (e.g. ~/.claude/projects/<cwd with / \\ : as ->) takes its newest .jsonl.
--turn N measures from the Nth user message to the next one (default: the whole file).
Prints: wall time (minus the time the person took to send each later message), model turns, tool calls by name, tokens, the slowest calls, the longest
waits between calls (model thinking/writing), the biggest tool outputs and files read twice.
"""
import argparse, collections, glob, json, os, sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))


def short(x, n=110):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return " ".join(s.split())[:n]


def size(c):
    if isinstance(c, str):
        return len(c)
    return sum(len(p.get("text", "")) if isinstance(p, dict) else len(str(p)) for p in c or [])


ap = argparse.ArgumentParser()
ap.add_argument("path")
ap.add_argument("--turn", type=int)
ap.add_argument("--from", dest="start")
ap.add_argument("--to", dest="end")
ap.add_argument("--top", type=int, default=12)
a = ap.parse_args()
path = a.path
if os.path.isdir(path):
    path = max(glob.glob(os.path.join(path, "*.jsonl")), key=os.path.getmtime)
rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
rows = [r for r in rows if r.get("timestamp") and isinstance(r.get("message"), dict)]

# typed user messages: not tool results, not skill bodies or images the harness injects (isMeta)
asks = [r for r in rows if r["type"] == "user" and not r.get("isMeta") and not r.get("toolUseResult")
        and not r.get("isSidechain") and (isinstance(r["message"].get("content"), str) or not any(
            isinstance(p, dict) and p.get("type") == "tool_result" for p in r["message"].get("content", [])))]
print(f"{os.path.basename(path)}\nuser messages:")
for i, r in enumerate(asks, 1):
    print(f"  {i:2} {r['timestamp']}  {short(r['message']['content'], 90)}")
t0, t1 = (ts(a.start) if a.start else None), (ts(a.end) if a.end else None)
if a.turn:
    t0 = ts(asks[a.turn - 1]["timestamp"])
    t1 = ts(asks[a.turn]["timestamp"]) if a.turn < len(asks) else None
win = [r for r in rows if (not t0 or ts(r["timestamp"]) >= t0) and (not t1 or ts(r["timestamp"]) < t1)]

usage, calls, results, last_t = {}, {}, {}, None
for r in win:
    c = r["message"].get("content")
    if r["type"] == "assistant":
        usage[r["message"].get("id")] = r["message"].get("usage", {})
        for p in c if isinstance(c, list) else []:
            if p.get("type") == "tool_use":
                calls[p["id"]] = (ts(r["timestamp"]), p["name"], p.get("input", {}))
    for p in c if isinstance(c, list) else []:
        if isinstance(p, dict) and p.get("type") == "tool_result":
            results[p["tool_use_id"]] = (ts(r["timestamp"]), size(p.get("content")))

start, end = ts(win[0]["timestamp"]), ts(win[-1]["timestamp"])
# time the person took to write each later message is theirs, not the run's: out of wall and waits
ask_ts = [ts(r["timestamp"]) for r in asks if start < ts(r["timestamp"]) <= end]
idle = 0.0
for at in ask_ts:
    before = [ts(r["timestamp"]) for r in win if ts(r["timestamp"]) < at]
    if before:
        idle += (at - max(before)).total_seconds()
u = lambda k: sum(x.get(k, 0) for x in usage.values())
idle_note = f" (+{idle:.0f}s waiting on the person, excluded)" if idle else ""
print(f"\nwall {(end - start).total_seconds() - idle:.0f}s{idle_note}  turns {len(usage)}  tool calls {len(calls)}  "
      f"output {u('output_tokens'):,}  cache read {u('cache_read_input_tokens'):,}  "
      f"cache write {u('cache_creation_input_tokens'):,}  input {u('input_tokens'):,}")
print("calls:", dict(collections.Counter(n for _, n, _ in calls.values()).most_common()))

line = lambda t, n, i: f"+{(t - start).total_seconds():5.0f}s {n:10} {short(i.get('command') or i.get('file_path') or i)}"
done = [(results[k][0] - t, t, n, i, results[k][1]) for k, (t, n, i) in calls.items() if k in results]
print(f"\nslowest calls (s):")
for d, t, n, i, _ in sorted(done, key=lambda x: -x[0])[:a.top]:
    print(f"  {d.total_seconds():5.1f}  {line(t, n, i)}")
print(f"\nbiggest outputs (chars):")
for d, t, n, i, s in sorted(done, key=lambda x: -x[4])[:a.top]:
    print(f"  {s:7,}  {line(t, n, i)}")

# model time: from a call's result, the start or a person's message to the next call
events = sorted([(t, "call", n, i) for t, n, i in calls.values()] + [(t, "res", None, None) for t, _ in results.values()]
                + [(t, "ask", None, None) for t in ask_ts], key=lambda e: e[0])
gaps, prev = [], start
for t, kind, n, i in events:
    if kind == "call":
        gaps.append(((t - prev).total_seconds(), t, n, i))
    prev = t
print(f"\nlongest model waits before a call (s), {sum(g for g, *_ in gaps):.0f}s in all:")
for g, t, n, i in sorted(gaps, key=lambda x: -x[0])[:a.top]:
    print(f"  {g:5.1f}  {line(t, n, i)}")

reads = collections.Counter(i.get("file_path") for _, n, i in calls.values() if n == "Read")
twice = {f: k for f, k in reads.items() if k > 1}
if twice:
    print("\nread more than once:", twice)
