---
name: skill-optimizer
description: Make an existing skill cheaper to run (fewer tokens, fewer steps, less wall time) without lowering the quality of what it produces, measured on a real run's transcript. Use when someone wants a skill "optimized", "faster", "cheaper", "with fewer steps or tokens", asks why a skill run took so long or cost so much, or wants to compare a skill's run before and after a change. Optimizing here is not shortening the SKILL.md; a longer skill that saves steps is a win.
---

# Skill optimizer

Goal, in order: fewer **tokens**, fewer **steps**, less **time**, with the same output quality.
A step (one model turn) is the expensive unit: each one resends the whole context (cache read) and thinks again. Merging two calls into one saves a context's worth of tokens and a round trip; trimming a sentence from SKILL.md saves almost nothing. So the skill may grow, if what it gains removes steps.

## 1. Measure a real run

Find the transcript: `~/.claude/projects/<project path with / \ : as ->/*.jsonl`. Ask the person which project and run if it isn't obvious.

```bash
python <skill>/scripts/measure.py ~/.claude/projects/<project> --turn N
```

It lists the user messages (pick `--turn` = the one that asked for the task), then wall time, turns, tool calls, tokens, the slowest calls, the longest model waits, the biggest tool outputs and files read twice. That is the baseline: write the numbers down. Don't read the raw jsonl by hand.

## 2. Map each waste to its cause

Read the parts of the run the numbers point at (`measure.py` output, then the skill's own text). Typical causes and fixes:

| Seen in the run | Cause in the skill | Fix |
| --- | --- | --- |
| Several calls doing mechanical work (loops, downloads, parsing, format conversion) | the agent rebuilds it each run | bundle a script that does it in one call and prints a compact result |
| Huge tool outputs (progress bars, JSON dumps, full logs) | commands with unfiltered output | give the exact filter (`| tail -3`, `grep`), or a script that summarizes |
| Independent steps one per turn | nothing says they can go together | say which steps go in the same message |
| Reading files it never uses (placeholders, other references, big docs) | unclear pointers | say what not to read; inline the few facts it opens a reference for |
| Retries, wrong flags, environment errors | the exact command or quirk is missing | write the working command; handle the known error inside the script |
| Opening a script or a tool's code to see how it behaves | behavior not documented | one line in SKILL.md on what it does and how to steer it |
| Re-checking what was already verified | no rule for when a check is enough | say when one check suffices and what still deserves a second look |
| Long model waits before a call | the agent deciding something the skill could decide | give the default; leave a real choice only where taste matters |

Keep the quality guidance (taste, review, checks that catch real defects). Automate the mechanical parts only; the agent keeps its freedom on creative and judgment calls.

## 3. Propose, then apply

List the changes ranked by expected savings (steps and seconds per run, estimated from the baseline), each one tied to the waste it removes. Show the diff and wait for approval before editing. Then apply, and test every new or changed script offline (sample inputs, a mocked API error) before calling it done.

## 4. Verify on a real run

The person runs the same kind of task with the updated skill (make sure the installed copy is the updated one). Measure it with the same `measure.py` command and compare to the baseline in one table: wall time, turns, tool calls, output tokens, cache read. Confirm with the person that the output is as good as before. Then read the new run for what still costs steps (`measure.py` again shows it) and repeat from step 2 if worth it.
