# skill-optimizer

A Claude Code skill that makes your other skills **cheaper and faster to run** without making their output worse.

It does not shorten your SKILL.md. It measures a real run from its transcript, finds where the steps, tokens and minutes went, and fixes the causes. Each model turn resends the whole context and thinks again, so one step saved is worth far more than a sentence trimmed. Often the optimized skill ends up longer.

## Results

First case: a video-editing skill (HyperFrames: voiceover, images, render). Same kind of task (a 35–40 s vertical video) before and after, with the same output quality:

| | Before | After | Change |
| --- | --- | --- | --- |
| Wall time | ~17 min | 11.4 min | −33% |
| Tool calls | 64 | 35 | −45% |
| Model turns | 46 | 27 | −41% |
| Output tokens | 53k | 42k | −22% |
| Cache-read tokens | 6.85M | 3.44M | −50% |

What changed: four small bundled scripts replaced work the agent rebuilt by hand on every run (parallel voice takes with timings, image search and download, fonts, a filtered check). Independent steps were batched into one message. Noisy command output was filtered. The facts the agent used to open reference files for were written inline. A second pass on the new transcript found the agent reading a script to understand its tempo logic, and that got fixed too.

This is one case so far. More are welcome.

## How it works

1. **Measure.** `scripts/measure.py` reads a run's transcript and prints, in one call: wall time, turns, tool calls by name, tokens, the slowest calls, the longest model waits, the biggest tool outputs and files read twice.
2. **Map waste to causes.** A table of common patterns: mechanical work worth a script, unfiltered output, serial steps that could go together, unneeded reads, retries, undocumented behavior, redundant checks, decisions the skill could make.
3. **Propose, then apply.** Changes ranked by expected savings, shown as a diff and applied only after approval. Scripts are tested offline.
4. **Verify.** Run the same kind of task again, measure it with the same command, compare the two in a table and confirm the output is as good as before.

Quality guidance stays: only the mechanical parts get automated, and the agent keeps its judgment on creative calls.

## Install

Copy this folder into your skills directory:

```bash
git clone https://github.com/CodeSquar/skill-optimizer.git ~/.claude/skills/skill-optimizer
```

Then ask Claude Code something like *"optimize my video-edit skill, here's the last run"* or *"why did that skill take 20 minutes?"*.

## Measure a run yourself

Transcripts live in `~/.claude/projects/<project path, with / \ : replaced by ->/*.jsonl`.

```bash
python scripts/measure.py ~/.claude/projects/<project> --turn 1
```

- A folder argument picks its newest transcript.
- `--turn N` measures from the Nth message you typed to the next one. Run it once without `--turn` to see the list.
- `--from` / `--to` take ISO timestamps for a custom window.
- `--top` sets how many rows each ranking shows.

Sample output (trimmed):

```
wall 698s  turns 28  tool calls 36  output 42,674  cache read 3,618,945  cache write 140,443  input 56
calls: {'Bash': 21, 'Read': 6, 'mcp__ccd_turn__update_plan': 4, 'Skill': 2, 'Write': 1, 'SendUserFile': 1, ...}

slowest calls (s):
  119.4  +  552s Bash       npx hyperframes render --quality delivery ...
biggest outputs (chars):
   15,889  +   18s Bash       cat "~/.claude/projects/.../old-run.jsonl" ...
longest model waits before a call (s), 402s in all:
  111.3  +  298s mcp__ccd_turn__update_plan ...
```

Requires Python 3.8+ and nothing else.

## Limits

- `measure.py` has only been tested on transcripts from the Claude Code desktop app on Windows. CLI, macOS, Linux and subagent sessions should work but haven't been checked yet.
- The before/after numbers come from one skill. Treat them as an example, not a promise.
