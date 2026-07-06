#!/usr/bin/env python3
"""Run an independent Codex vision review for mission CSV REVIEW rows."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path


RESULT_KEYS = {
    "review_agent_mode",
    "review_independence",
    "result",
    "claim_coverage",
    "claim_coverage_status",
    "actual_model",
    "validation_limited",
    "summary",
    "gaps",
    "assumptions",
    "decision_debt",
    "human_required_blockers",
    "handoff_markdown",
}

CLAIMS_RE = re.compile(r"(?:^|;\s*)claims:([^;]+)")
LEDGER_RE = re.compile(r"(?:^|;\s*)claim_ledger:([^;]+)")


def existing_file(value: str, workdir: Path) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"file does not exist: {value}")
    return str(path.resolve())


def resolve_existing_file(value: str, workdir: Path, base_dir: Path | None = None) -> str:
    path = Path(value).expanduser()
    if path.is_absolute():
        candidates = [path]
    else:
        candidates = [workdir / path]
        if base_dir:
            candidates.append(base_dir / path)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise argparse.ArgumentTypeError(f"file does not exist: {value}")


def optional_file(value: str | None, workdir: Path) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    if not path.exists():
        return str(path.resolve())
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {value}")
    return str(path.resolve())


def tag_value(pattern: re.Pattern[str], notes: str) -> str | None:
    match = pattern.search(notes or "")
    return match.group(1).strip() if match else None


def discover_claim_ledger(csv_path: str, workdir: Path) -> str | None:
    path = Path(csv_path)
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig", newline="")))
    has_claims = False
    ledger_values: list[str] = []
    for row in rows:
        notes = row.get("notes", "")
        if tag_value(CLAIMS_RE, notes):
            has_claims = True
        ledger = tag_value(LEDGER_RE, notes)
        if ledger and ledger not in ledger_values:
            ledger_values.append(ledger)
    if not ledger_values:
        if has_claims:
            raise argparse.ArgumentTypeError("CSV has claims but no claim_ledger tag")
        return None
    if len(ledger_values) > 1:
        raise argparse.ArgumentTypeError("CSV references multiple claim ledgers: " + ", ".join(ledger_values))
    return resolve_existing_file(ledger_values[0], workdir, path.parent)


def output_file(value: str, workdir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = workdir / path
    return path.resolve()


def build_prompt(args: argparse.Namespace) -> str:
    mode_instruction = (
        "First spawn one default same-model subagent to perform the review, wait for it, "
        "then return the child review JSON unchanged. If native spawn_agent is unavailable "
        "inside this exec session, perform the review yourself and set "
        "`review_agent_mode` to `codex-exec-independent`."
        if not args.no_subagent
        else "Perform the review in this independent codex exec session and set "
        "`review_agent_mode` to `codex-exec-independent`."
    )
    review_log = args.review_log or "(review log does not exist yet)"
    claim_ledger = args.claim_ledger or "(claim ledger not provided)"
    extra = args.extra or "None"
    return f"""You are a mission vision review orchestrator.

{mode_instruction}

Reviewer task:
- Work read-only.
- Do not trust the main agent's conclusions or summaries.
- Read the approved source document, task CSV, review log if present, and relevant code/test evidence referenced by the CSV.
- Inspect git history/diff only as needed to verify delivered work and claims.
- Reconstruct or verify the claim/evidence ledger: source claims, covered issue ids, production paths, and evidence level.
- Do not find issues for its own sake. A gap must be falsifiable and tied to a source claim or overstated delivery claim.

Inputs:
- Source doc: {args.source_doc}
- Task CSV: {args.csv}
- Claim ledger JSON: {claim_ledger}
- Review log: {review_log}
- Requested model: {args.model or "Codex CLI default model"}
- Extra evidence: {extra}

Return exactly one JSON object and no markdown. Schema:
{{
  "review_agent_mode": "codex-exec-subagent | codex-exec-independent",
  "review_independence": "strong",
  "result": "vision_met | gaps_found | limited_review",
  "claim_coverage": "covered/total, for example 12/13; use unknown only with limited_review",
  "claim_coverage_status": "complete | gaps | unknown",
  "actual_model": "model id if known, else unknown",
  "validation_limited": ["model parity unknown"],
  "summary": "one concise paragraph",
  "gaps": [
    {{
      "id": "FOLLOWUP-01",
      "title": "short executable issue title",
      "source_ref": "path:line",
      "evidence_ref": "path:line or command/log reference",
      "why_it_matters": "why this violates the approved doc or claim/evidence alignment",
      "suggested_followup_issue": "one sentence executable issue"
    }}
  ],
  "assumptions": ["..."],
  "decision_debt": ["..."],
  "human_required_blockers": ["..."],
  "handoff_markdown": "Full human-facing handoff in Markdown. Follow the Handoff template below exactly. Audience is a non-expert human decision-maker, not a machine."
}}

Rules:
- Use result `vision_met` only when claim coverage is complete or explicitly out-of-scope, no actionable gaps remain, and evidence levels are honestly labeled.
- Use result `gaps_found` for actionable discrepancies.
- Use result `limited_review` if you cannot inspect enough evidence or cannot perform independent review.
- If exact model parity cannot be confirmed, set `actual_model` to `unknown`, include `model parity unknown` in `validation_limited`, and mention it in `assumptions`.
- If there are no gaps, return an empty `gaps` array.

Handoff template (handoff_markdown):
Write a complete Markdown document that reads like a "construction completion report". The reader is the person who wrote or approved the spec -- they come back days later and need to understand what got done, without opening CSV, claims.json, or git log.

Write in the SAME style as the source design doc: use comparison tables, arrow-flow diagrams, conclusion sentences, inline term definitions. NOT audit-log style.

HARD RULES for handoff style:
- Structure follows the spec's goals/capabilities, NOT CSV row numbers, NOT CLAIM-XXX IDs
- Self-contained: inline all information. Never write "see claims.json" or reference CLAIM-XXX
- Plain language first: say "users can now search for contact emails" BEFORE saying "research_contacts returns non-empty list"
- Explain terms on first use with parentheses
- No review audit jargon: never write "scope checked", "evidence checked", "claim coverage", "vision_met"
- Honest: if something is degraded or unverified, say so plainly. Thin evidence = thin section, never pad
- handoff_markdown is REQUIRED even when result is limited_review

Required structure:

# <task topic> -- 施工交工单

> 独立性: <review_agent_mode> | <review_independence> | model=<actual_model>
> 日期: <date>

(If review_independence is weak, add: "WARNING: self-review only, NOT independently verified")

## 总结

One paragraph, plain language: what spec this implements, how many of the spec's core goals are fulfilled, whether there are degraded items or blockers. A non-technical manager should understand this paragraph.

## spec 目标逐条对账

Use a table or numbered list. One row per spec goal (NOT per CSV issue). Columns:

| spec 目标 | 状态 | 实际效果 | 备注 |
|-----------|------|----------|------|

- "spec 目标": extract from source doc using the spec's own wording (condense if too long)
- "状态": 完成 / 部分完成 / 降级 / 未开始
- "实际效果": describe from user/product perspective what changed
- "备注": if degraded/incomplete, explain why and what's missing

## 施工细节

Organize by module or functional area (NOT by CSV row). For each area:
- What changed: which files/functions, before vs after (use arrow-flow or comparison table)
- Problems hit: issues discovered during execution, root cause, how fixed
- Decisions made: choices the spec didn't prescribe, what was chosen, why

Example format:
```
改之前：chat runtime 没有注入 store → remember_user_memory 报错
改之后：main.py:112 暴露 store → chat.py:172 注入 → 工具正常写入
```

When this round changes multi-layer data flow, cross-file call relationships, or architecture boundaries (responsibility moved/demoted/promoted), you MUST add a mermaid diagram here, not just text:
- At most two diagrams: one "改之前", one "改之后", so the reader sees the change as a diff. One diagram is fine if only one side changed.
- Draw ONLY nodes/edges related to this change, never the whole system (a full-system map drowns the change point).
- Mark what changed: in the "改后" diagram, label the new/changed node or edge (e.g. a dotted edge `-.本轮新增.->`).
- Do NOT force a diagram for text-only edits, single-function internal logic, or changes with no cross-file/cross-layer relationship -- thin source = thin section, never pad with visuals.
- Fallback: if mermaid cannot be written or fails to render, fall back to the ASCII arrow block above. A diagram must never block the handoff.

mermaid example (改后 data flow; dotted edge = added this round):
```mermaid
flowchart LR
    A[main.py:112 暴露 store] --> B[chat.py:172 注入]
    B -.本轮新增.-> C[remember_user_memory 正常写入]
```

## 验证情况

Brief (this is NOT the main section):
- What tests ran, results (one or two lines)
- What was NOT verified and why (honestly)

## 后续可操作

Only include subsections that apply -- do not write empty subsections:

**还剩什么**: unfinished items, items needing product decisions, known limitations

**阻塞/配置**: things the user must do (configure credentials, start services, approve something). State the exact unblock condition.

**怎么复现** (if applicable): complete E2E steps -- what to start, what to input, what result to expect

**去哪看** (if applicable): addresses, filter conditions, DB queries, log paths for any observable data relevant to this work
"""


def parse_json_events(stdout: str) -> tuple[str | None, bool]:
    final_message = None
    saw_spawn = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        if item.get("type") == "collab_tool_call" and item.get("tool") == "spawn_agent":
            saw_spawn = True
        if item.get("type") == "collab_tool_call" and item.get("tool_name") == "spawn_agent":
            saw_spawn = True
        if payload.get("type") == "function_call" and payload.get("name") == "spawn_agent":
            saw_spawn = True
        if payload.get("type") == "collab_tool_call" and payload.get("tool") == "spawn_agent":
            saw_spawn = True
        if item.get("type") == "agent_message":
            final_message = item.get("text")
        if item.get("type") == "message" and item.get("role") == "assistant":
            parts = []
            for content in item.get("content") or []:
                if isinstance(content, dict):
                    text = content.get("text") or content.get("output_text")
                    if text:
                        parts.append(text)
            if parts:
                final_message = "\n".join(parts)
        if event.get("type") == "agent_message":
            final_message = event.get("message") or event.get("text") or payload.get("message")
        if event.get("type") == "event_msg" and payload.get("type") == "agent_message":
            final_message = payload.get("message")
        if event.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            parts = []
            for content in payload.get("content") or []:
                if isinstance(content, dict):
                    text = content.get("text") or content.get("output_text")
                    if text:
                        parts.append(text)
            if parts:
                final_message = "\n".join(parts)
    return final_message, saw_spawn


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--source-doc", required=True)
    parser.add_argument("--claim-ledger", help="Claim/evidence ledger JSON. Defaults to claim_ledger tag discovered from the CSV.")
    parser.add_argument("--review-log")
    parser.add_argument("--extra", help="Short extra evidence summary or path list.")
    parser.add_argument("--workdir", default=os.getcwd())
    parser.add_argument("--model", default=os.environ.get("CODEX_REVIEW_MODEL"), help="Reviewer model. Defaults to Codex CLI's configured model.")
    parser.add_argument("--output", help="Write final JSON to this file.")
    parser.add_argument("--handoff", help="Write handoff_markdown to this .md file.")
    parser.add_argument("--no-subagent", action="store_true", help="Do not ask codex exec to spawn a child reviewer.")
    args = parser.parse_args()

    workdir_path = Path(args.workdir).expanduser().resolve()
    args.csv = existing_file(args.csv, workdir_path)
    args.source_doc = existing_file(args.source_doc, workdir_path)
    args.claim_ledger = (
        resolve_existing_file(args.claim_ledger, workdir_path, Path(args.csv).parent)
        if args.claim_ledger
        else discover_claim_ledger(args.csv, workdir_path)
    )
    args.review_log = optional_file(args.review_log, workdir_path)
    workdir = str(workdir_path)
    prompt = build_prompt(args)
    cmd = [
        "codex",
        "exec",
        "--ephemeral",
        "--json",
        "--skip-git-repo-check",
    ]
    if args.model:
        cmd.extend(["-m", args.model])
    cmd.extend([
        "-C",
        workdir,
        "--sandbox",
        "read-only",
        "-",
    ])
    proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.stderr.write(proc.stdout)
        return proc.returncode

    final_message, saw_spawn = parse_json_events(proc.stdout)
    if not final_message:
        sys.stderr.write("codex exec produced no final agent message\n")
        return 2
    try:
        result = json.loads(final_message)
    except json.JSONDecodeError:
        sys.stderr.write("final agent message was not valid JSON\n")
        sys.stderr.write(final_message + "\n")
        return 3
    if not isinstance(result, dict):
        sys.stderr.write("final agent message JSON root must be an object\n")
        return 4

    missing = sorted(RESULT_KEYS - set(result))
    if missing:
        sys.stderr.write("review JSON missing required keys: " + ", ".join(missing) + "\n")
        return 4
    claim_coverage = str(result.get("claim_coverage"))
    if claim_coverage != "unknown" and not re.fullmatch(r"\d+/\d+", claim_coverage):
        sys.stderr.write("claim_coverage must be '<covered>/<total>' or 'unknown'\n")
        return 5
    if claim_coverage == "unknown" and result.get("result") != "limited_review":
        sys.stderr.write("claim_coverage may be unknown only for limited_review\n")
        return 5
    validation_limited = result.get("validation_limited")
    if not isinstance(validation_limited, list):
        sys.stderr.write("validation_limited must be a list\n")
        return 6
    if not args.model and "model parity unknown" not in validation_limited:
        validation_limited.append("model parity unknown")
    if not args.model and not result.get("actual_model"):
        result["actual_model"] = "unknown"
    if saw_spawn and result.get("review_agent_mode") == "codex-exec-independent":
        result["review_agent_mode"] = "codex-exec-subagent"
    result.setdefault("review_independence", "strong")

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = output_file(args.output, workdir_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    if args.handoff:
        handoff_md = result.get("handoff_markdown")
        if handoff_md:
            handoff_path = output_file(args.handoff, workdir_path)
            handoff_path.parent.mkdir(parents=True, exist_ok=True)
            handoff_path.write_text(handoff_md.rstrip() + "\n", encoding="utf-8")
        else:
            sys.stderr.write("warning: --handoff requested but review JSON had no handoff_markdown\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
