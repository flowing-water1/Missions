#!/usr/bin/env python3
"""Run an independent Codex vision review for mission CSV REVIEW rows."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from validate_outcome_contract import load_contract


RESULT_KEYS = {
    "review_agent_mode",
    "review_independence",
    "review_requested_model",
    "review_observed_model",
    "review_model_evidence",
    "result",
    "claim_coverage",
    "claim_coverage_status",
    "validation_limited",
    "summary",
    "gaps",
    "assumptions",
    "decision_debt",
    "deferred_findings",
    "human_required_blockers",
    "outcome_answers",
    "handoff_markdown",
}

DEFAULT_REVIEW_MODEL = "gpt-5.6-sol"
MODEL_EVIDENCE = {"session-metadata", "event-stream", "parent-runtime", "unknown"}

CLAIMS_RE = re.compile(r"(?:^|;\s*)claims:([^;]+)")
LEDGER_RE = re.compile(r"(?:^|;\s*)claim_ledger:([^;]+)")
OUTCOME_RE = re.compile(r"(?:^|;\s*)outcome_contract:([^;]+)")
DEFERRED_RE = re.compile(r"(?:^|;\s*)deferred_ledger:([^;]+)")
OUTCOME_VERDICTS = {"pass", "fail", "partial", "unknown", "not_run"}
OUTCOME_CONFIDENCE = {"high", "moderate", "low", "unknown"}


def normalize_review_mode(mode: str) -> tuple[str, bool | str, bool]:
    """Return new mode, independence, and whether a diff-only pass is supplemental."""
    mapping: dict[str, tuple[str, bool | str, bool]] = {
        "direct-spawn-agent": ("reviewer-subagent", True, False),
        "direct-same-model-subagent": ("reviewer-subagent", True, False),
        "reviewer-subagent": ("reviewer-subagent", True, False),
        "codex-exec-subagent": ("codex-exec-independent", True, False),
        "codex-exec-independent": ("codex-exec-independent", True, False),
        "codex-review-diff-only": ("self-review", False, True),
        "codex-review-independent": ("self-review", False, True),
        "main-session-fallback": ("self-review", False, False),
        "self-review": ("self-review", False, False),
        "pending": ("pending", "pending", False),
    }
    if mode not in mapping:
        raise ValueError(f"unknown review mode: {mode}")
    return mapping[mode]


def resolve_codex_executable(which=shutil.which) -> str | None:
    """Resolve the platform launcher, including codex.CMD on Windows."""
    return which("codex")


def build_exec_command(executable: str, workdir: str, model: str) -> list[str]:
    return [
        executable,
        "exec",
        "--ephemeral",
        "--json",
        "--skip-git-repo-check",
        "-m",
        model,
        "-C",
        workdir,
        "--sandbox",
        "read-only",
        "-",
    ]


def run_codex_exec(cmd: list[str], prompt: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        input=prompt,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


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
        candidates = []
        if base_dir:
            candidates.append(base_dir / path)
        candidates.append(workdir / path)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.resolve())
    raise argparse.ArgumentTypeError(f"file does not exist: {value}")


def artifact_output_path(value: str, workdir: Path, base_dir: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    if base_dir and (not path.parts or path.parts[0] != "issues"):
        return (base_dir / path).resolve()
    return (workdir / path).resolve()


def optional_file(value: str | None, workdir: Path, base_dir: Path | None = None) -> str | None:
    if not value:
        return None
    path = artifact_output_path(value, workdir, base_dir)
    if not path.exists():
        return str(path)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {value}")
    return str(path)


def tag_value(pattern: re.Pattern[str], notes: str) -> str | None:
    match = pattern.search(notes or "")
    return match.group(1).strip() if match else None


def discover_claim_ledger(csv_path: str, workdir: Path) -> str | None:
    path = Path(csv_path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
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


def discover_outcome_contract(csv_path: str, workdir: Path) -> str | None:
    path = Path(csv_path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values: list[str] = []
    for row in rows:
        value = tag_value(OUTCOME_RE, row.get("notes", ""))
        if value and value not in values:
            values.append(value)
    if not values:
        return None
    if len(values) > 1:
        raise argparse.ArgumentTypeError(
            "CSV references multiple outcome contracts: " + ", ".join(values)
        )
    return resolve_existing_file(values[0], workdir, path.parent)


def discover_deferred_ledger(csv_path: str, workdir: Path) -> str | None:
    path = Path(csv_path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values: list[str] = []
    for row in rows:
        value = tag_value(DEFERRED_RE, row.get("notes", ""))
        if value and value not in values:
            values.append(value)
    if not values:
        return None
    if len(values) > 1:
        raise argparse.ArgumentTypeError(
            "CSV references multiple deferred ledgers: " + ", ".join(values)
        )
    return resolve_existing_file(values[0], workdir, path.parent)


def validate_outcome_answers(result: dict, contract: dict | None) -> list[str]:
    answers = result.get("outcome_answers")
    if not isinstance(answers, list):
        return ["outcome_answers must be a list"]

    expected = {
        question.get("id")
        for question in (contract or {}).get("reader_questions", [])
        if isinstance(question, dict) and question.get("id")
    }
    seen: set[str] = set()
    errors: list[str] = []
    for index, answer in enumerate(answers):
        if not isinstance(answer, dict):
            errors.append(f"outcome_answers[{index}] must be an object")
            continue
        question_id = answer.get("question_id")
        if not isinstance(question_id, str) or not question_id:
            errors.append(f"outcome_answers[{index}] missing question_id")
            continue
        if question_id in seen:
            errors.append(f"duplicate outcome answer: {question_id}")
        seen.add(question_id)
        if question_id not in expected:
            errors.append(f"unexpected outcome answer: {question_id}")
        verdict = answer.get("verdict")
        if verdict not in OUTCOME_VERDICTS:
            errors.append(f"{question_id} has invalid verdict: {verdict}")
        confidence = answer.get("confidence")
        if confidence not in OUTCOME_CONFIDENCE:
            errors.append(f"{question_id} has invalid confidence: {confidence}")
        for key in ("answer", "boundary", "next_action"):
            if not isinstance(answer.get(key), str) or not answer[key].strip():
                errors.append(f"{question_id} missing {key}")
        refs = answer.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not all(
            isinstance(value, str) and value.strip() for value in refs
        ):
            errors.append(f"{question_id} evidence_refs must be a non-empty string array")
    for question_id in sorted(expected - seen):
        errors.append(f"missing outcome answer: {question_id}")
    return errors


def output_file(value: str, workdir: Path, base_dir: Path | None = None) -> Path:
    path = artifact_output_path(value, workdir, base_dir)
    artifact_root = (base_dir or workdir).resolve()
    try:
        path.relative_to(artifact_root)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"output path escapes artifact root {artifact_root}: {path}"
        ) from exc
    return path


def _string_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def validate_review_result(result: dict, contract: dict | None) -> list[str]:
    errors: list[str] = []
    missing = sorted(RESULT_KEYS - set(result))
    if missing:
        errors.append("review JSON missing required keys: " + ", ".join(missing))
        return errors

    mode = result.get("review_agent_mode")
    independence = result.get("review_independence")
    if mode not in {"reviewer-subagent", "codex-exec-independent", "self-review"}:
        errors.append(f"invalid review_agent_mode: {result.get('review_agent_mode')}")
    if not isinstance(independence, bool):
        errors.append(f"invalid review_independence: {result.get('review_independence')}")
    elif mode in {"reviewer-subagent", "codex-exec-independent"} and not independence:
        errors.append(f"{mode} requires review_independence=true")
    elif mode == "self-review" and independence:
        errors.append("self-review requires review_independence=false")
    if result.get("review_requested_model") != DEFAULT_REVIEW_MODEL:
        errors.append(f"review_requested_model must be {DEFAULT_REVIEW_MODEL}")
    if not isinstance(result.get("review_observed_model"), str) or not result[
        "review_observed_model"
    ].strip():
        errors.append("review_observed_model must be a non-empty string")
    if result.get("review_model_evidence") not in MODEL_EVIDENCE:
        errors.append(f"invalid review_model_evidence: {result.get('review_model_evidence')}")
    if result.get("result") not in {"vision_met", "gaps_found", "limited_review"}:
        errors.append(f"invalid review result: {result.get('result')}")
    if result.get("claim_coverage_status") not in {"complete", "gaps", "unknown"}:
        errors.append(f"invalid claim_coverage_status: {result.get('claim_coverage_status')}")
    for key in ("summary", "handoff_markdown"):
        if not isinstance(result.get(key), str) or not result[key].strip():
            errors.append(f"{key} must be a non-empty string")
    for key in (
        "validation_limited",
        "assumptions",
        "decision_debt",
        "human_required_blockers",
    ):
        if not _string_list(result.get(key)):
            errors.append(f"{key} must be a string array")

    gaps = result.get("gaps")
    if not isinstance(gaps, list):
        errors.append("gaps must be an array")
        gaps = []
    else:
        for index, gap in enumerate(gaps):
            if not isinstance(gap, dict):
                errors.append(f"gaps[{index}] must be an object")
                continue
            for key in (
                "id",
                "title",
                "source_ref",
                "evidence_ref",
                "why_it_matters",
                "suggested_followup_issue",
            ):
                if not isinstance(gap.get(key), str) or not gap[key].strip():
                    errors.append(f"gaps[{index}] missing {key}")

    deferred_findings = result.get("deferred_findings")
    if not isinstance(deferred_findings, list):
        errors.append("deferred_findings must be an array")
    else:
        for index, finding in enumerate(deferred_findings):
            if not isinstance(finding, dict):
                errors.append(f"deferred_findings[{index}] must be an object")
                continue
            kind = finding.get("kind")
            if kind not in {"deferred_improvement", "future_decision"}:
                errors.append(f"deferred_findings[{index}] has invalid kind: {kind}")
            for key in (
                "id",
                "title",
                "summary",
                "why_deferred",
                "discussion_question",
            ):
                if not isinstance(finding.get(key), str) or not finding[key].strip():
                    errors.append(f"deferred_findings[{index}] missing {key}")
            for key in ("source_issue_ids", "evidence_refs"):
                value = finding.get(key)
                if not isinstance(value, list) or not value or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    errors.append(f"deferred_findings[{index}] {key} must be a non-empty string array")

    coverage = str(result.get("claim_coverage"))
    covered = total = None
    if coverage != "unknown":
        match = re.fullmatch(r"(\d+)/(\d+)", coverage)
        if not match:
            errors.append("claim_coverage must be '<covered>/<total>' or 'unknown'")
        else:
            covered, total = (int(match.group(1)), int(match.group(2)))
            if covered > total:
                errors.append("claim_coverage covered count cannot exceed total")
    if coverage == "unknown" and result.get("result") != "limited_review":
        errors.append("claim_coverage may be unknown only for limited_review")
    if result.get("claim_coverage_status") == "complete" and covered is not None and covered != total:
        errors.append("claim_coverage_status=complete requires covered=total")
    if result.get("claim_coverage_status") == "gaps" and covered is not None and covered >= total:
        errors.append("claim_coverage_status=gaps requires covered<total")
    if result.get("claim_coverage_status") == "unknown" and coverage != "unknown":
        errors.append("claim_coverage_status=unknown requires claim_coverage=unknown")

    errors.extend(validate_outcome_answers(result, contract))

    if result.get("result") == "vision_met":
        if result.get("claim_coverage_status") != "complete":
            errors.append("vision_met requires claim_coverage_status=complete")
        if gaps:
            errors.append("vision_met requires an empty gaps array")
        if result.get("human_required_blockers"):
            errors.append("vision_met cannot have human_required_blockers")
        answers = result.get("outcome_answers") or []
        if any(answer.get("verdict") != "pass" for answer in answers if isinstance(answer, dict)):
            errors.append("vision_met requires every outcome verdict to be pass")
    if result.get("result") == "gaps_found":
        answers = result.get("outcome_answers") or []
        has_non_pass_outcome = any(
            answer.get("verdict") != "pass" for answer in answers if isinstance(answer, dict)
        )
        if (
            not gaps
            and result.get("claim_coverage_status") != "gaps"
            and not result.get("human_required_blockers")
            and not has_non_pass_outcome
        ):
            errors.append("gaps_found requires a recorded gap signal")
    return errors


def build_prompt(args: argparse.Namespace) -> str:
    review_log = args.review_log or "(review log does not exist yet)"
    claim_ledger = args.claim_ledger or "(claim ledger not provided)"
    outcome_contract = args.outcome_contract or "(outcome contract not provided; return an empty outcome_answers array)"
    deferred_ledger = args.deferred_ledger or "(deferred ledger not provided; start ids at DF-001 if needed)"
    source_doc = args.source_doc or "(no approved spec; this is an explicit compatibility CSV)"
    extra = args.extra or "None"
    return f"""You are the independent mission vision reviewer in an ephemeral, read-only Codex exec session.

Reviewer task:
- Work read-only.
- Do not trust the main agent's conclusions or summaries.
- Read the approved source document, task CSV, review log if present, and relevant code/test evidence referenced by the CSV.
- Inspect git history/diff only as needed to verify delivered work and claims.
- Reconstruct or verify the claim/evidence ledger: source claims, covered issue ids, production paths, and evidence level.
- Do not find issues for its own sake. A gap must be falsifiable and tied to a source claim or overstated delivery claim.

Inputs:
- Source doc: {source_doc}
- Source CSV: {args.csv}
- Task CSV: {args.csv}
- Claim ledger JSON: {claim_ledger}
- Outcome Contract JSON: {outcome_contract}
- Deferred findings ledger JSON: {deferred_ledger}
- Review log: {review_log}
- Requested model: {args.model or "Codex CLI default model"}
- Extra evidence: {extra}

Return exactly one JSON object and no markdown. Schema:
{{
  "result": "vision_met | gaps_found | limited_review",
  "claim_coverage": "covered/total, for example 12/13; use unknown only with limited_review",
  "claim_coverage_status": "complete | gaps | unknown",
  "validation_limited": ["evidence limitation, if any"],
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
  "deferred_findings": [
    {{
      "id": "DF-001",
      "kind": "deferred_improvement | future_decision",
      "title": "short human-readable title",
      "summary": "what was observed",
      "source_issue_ids": ["REVIEW-01"],
      "evidence_refs": ["trace/test/artifact reference"],
      "why_deferred": "why this does not block the current approved scope",
      "discussion_question": "the concrete question for the user"
    }}
  ],
  "human_required_blockers": ["..."],
  "outcome_answers": [
    {{
      "question_id": "OUTCOME-001",
      "verdict": "pass | fail | partial | unknown | not_run",
      "answer": "direct answer to the reader question",
      "evidence_refs": ["trace/test/artifact reference"],
      "confidence": "high | moderate | low | unknown",
      "boundary": "what this evidence cannot establish",
      "next_action": "how to resolve fail, partial, unknown, or not_run; write None only when no action is needed"
    }}
  ],
  "handoff_markdown": "Full human-facing handoff in Markdown. Follow the Handoff template below exactly. Audience is a non-expert human decision-maker, not a machine."
}}

Rules:
- Use result `vision_met` only when claim coverage is complete or explicitly out-of-scope, no actionable gaps remain, and evidence levels are honestly labeled.
- Use result `gaps_found` for actionable discrepancies.
- Use result `limited_review` if you cannot inspect enough evidence or cannot perform independent review.
- If there are no gaps, return an empty `gaps` array.
- Classify every discovery before reporting it. A current-scope gap violates the approved source or an acceptance criterion; it belongs in `gaps` and must not be deferred.
- Use `deferred_improvement` only for a non-blocking quality or architecture improvement outside the current approved scope. Use `future_decision` only when the current scope is complete but a later product or architecture choice needs the user.
- `deferred_findings` contains only those two non-blocking kinds. Preserve existing open findings from the ledger, deduplicate by meaning and evidence, and allocate the next DF number for new findings.
- Never append or execute a CSV issue for a deferred finding. The mission ends after the current CSV and presents these items for user discussion.
- If an Outcome Contract is provided, return exactly one outcome answer for every reader question.
- Do not infer pass from implementation status. Use only cited evidence, and preserve `unknown` or `not_run` when evidence is absent.
- If no Outcome Contract is provided, return an empty `outcome_answers` array for legacy compatibility.

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

Required structure when an Outcome Contract is provided:

# <task topic> -- 施工交工单

> 独立性: true | mode=codex-exec-independent | requested_model={args.model}
> 日期: <date>

## 先看结论

One paragraph with the overall verdict, decisive result, and most important blocked claim. A non-technical manager should understand it.

## 这份交工单告诉你什么

State the artifact role, evidence inputs, consumers, and what the handoff does not prove or override.

## 你现在可以确定什么

Render every reader question from the Outcome Contract. Use this table:

| 你关心的问题 | 判定 | 直接答案 | 关键证据 | 可信度 | 结论边界 | 下一步 |
|---|---|---|---|---|---|---|

Do not expose OUTCOME-* ids. Keep the question text unchanged so contract validation can match it.
Copy verdict, answer, confidence, boundary, and next_action exactly from outcome_answers. Join multiple evidence_refs with the literal separator `; `. These table cells are machine-checked and must not be paraphrased later.

## 决定整体状态的结果

Explain the decisive end-to-end result, the last confirmed healthy stage, and the first failure or evidence gap. Separate implementation status, validation status, and capability verdict.

## 目前仍不能声称什么

Render every blocked claim with its reason and release condition. Never aggregate partial, unknown, or not_run into pass.
Copy claim, reason, and release_condition exactly from the Outcome Contract; these cells are machine-checked.

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

## 待讨论

Include this section only when the deferred ledger has open findings or `deferred_findings` is non-empty. Render every open deferred finding from the ledger plus every new item in natural language. Put `<!-- deferred:DF-001 -->` immediately before its text so coverage can be checked. Keep ids out of visible headings and prose.

## 后续可操作

Only include subsections that apply -- do not write empty subsections:

**还剩什么**: unfinished items, items needing product decisions, known limitations

**阻塞/配置**: things the user must do (configure credentials, start services, approve something). State the exact unblock condition.

**怎么复现** (if applicable): complete E2E steps -- what to start, what to input, what result to expect

**去哪看** (if applicable): addresses, filter conditions, DB queries, log paths for any observable data relevant to this work

Legacy fallback: when no Outcome Contract is provided, keep the existing summary, spec-goal reconciliation, construction details, validation, and next-action structure. Do not invent reader questions.
"""


def _trusted_event_model(event: dict) -> str | None:
    event_type = event.get("type")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload_type = payload.get("type")
    trusted_types = {
        "thread.started",
        "session_meta",
        "session_metadata",
        "turn.started",
        "response.started",
    }
    if event_type not in trusted_types and payload_type not in trusted_types:
        return None
    for container in (event, payload):
        for key in ("model", "model_id"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def parse_json_events(stdout: str) -> tuple[str | None, str | None]:
    final_message = None
    observed_model = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        observed_model = _trusted_event_model(event) or observed_model
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
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
    return final_message, observed_model


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--source-doc")
    parser.add_argument("--claim-ledger", help="Claim/evidence ledger JSON. Defaults to claim_ledger tag discovered from the CSV.")
    parser.add_argument("--outcome-contract", help="Outcome Contract JSON. Defaults to outcome_contract tag discovered from the CSV.")
    parser.add_argument("--deferred-ledger", help="Deferred findings ledger JSON. Defaults to deferred_ledger tag discovered from the CSV.")
    parser.add_argument("--review-log")
    parser.add_argument("--extra", help="Short extra evidence summary or path list.")
    parser.add_argument("--workdir", default=os.getcwd())
    parser.add_argument(
        "--model",
        default=os.environ.get("CODEX_REVIEW_MODEL", DEFAULT_REVIEW_MODEL),
        help=f"Reviewer model. Defaults to {DEFAULT_REVIEW_MODEL}.",
    )
    parser.add_argument("--output", help="Write final JSON to this file.")
    parser.add_argument("--handoff", help="Write handoff_markdown to this .md file.")
    args = parser.parse_args()

    workdir_path = Path(args.workdir).expanduser().resolve()
    args.csv = existing_file(args.csv, workdir_path)
    args.source_doc = existing_file(args.source_doc, workdir_path) if args.source_doc else None
    args.claim_ledger = (
        resolve_existing_file(args.claim_ledger, workdir_path, Path(args.csv).parent)
        if args.claim_ledger
        else discover_claim_ledger(args.csv, workdir_path)
    )
    args.outcome_contract = (
        resolve_existing_file(args.outcome_contract, workdir_path, Path(args.csv).parent)
        if args.outcome_contract
        else discover_outcome_contract(args.csv, workdir_path)
    )
    args.deferred_ledger = (
        resolve_existing_file(args.deferred_ledger, workdir_path, Path(args.csv).parent)
        if args.deferred_ledger
        else discover_deferred_ledger(args.csv, workdir_path)
    )
    outcome_contract_data = None
    if args.outcome_contract:
        outcome_contract_data, contract_errors = load_contract(Path(args.outcome_contract))
        if contract_errors:
            for error in contract_errors:
                sys.stderr.write(error + "\n")
            return 5
    csv_dir = Path(args.csv).parent
    args.review_log = optional_file(args.review_log, workdir_path, csv_dir)
    output_path = output_file(args.output, workdir_path, csv_dir) if args.output else None
    handoff_path = output_file(args.handoff, workdir_path, csv_dir) if args.handoff else None
    workdir = str(workdir_path)
    prompt = build_prompt(args)
    executable = resolve_codex_executable()
    if not executable:
        sys.stderr.write("codex executable not found; continue with self-review fallback\n")
        return 127
    cmd = build_exec_command(executable, workdir, args.model)
    proc = run_codex_exec(cmd, prompt)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        sys.stderr.write(proc.stdout)
        return proc.returncode

    final_message, observed_model = parse_json_events(proc.stdout)
    if not final_message:
        sys.stderr.write("codex exec produced no final agent message\n")
        return 2
    try:
        result = json.loads(final_message)
    except json.JSONDecodeError:
        sys.stderr.write("final agent message was not valid JSON\n")
        sys.stderr.write(final_message + "\n")
        return 3

    for untrusted_key in (
        "actual_model",
        "review_agent_mode",
        "review_independence",
        "review_requested_model",
        "review_observed_model",
        "review_model_evidence",
    ):
        result.pop(untrusted_key, None)
    result.update(
        {
            "review_agent_mode": "codex-exec-independent",
            "review_independence": True,
            "review_requested_model": args.model,
            "review_observed_model": observed_model or "unknown",
            "review_model_evidence": "event-stream" if observed_model else "unknown",
        }
    )
    review_errors = validate_review_result(result, outcome_contract_data)
    if review_errors:
        for error in review_errors:
            sys.stderr.write(error + "\n")
        return 5
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    if handoff_path:
        handoff_md = result.get("handoff_markdown")
        if handoff_md:
            handoff_path.parent.mkdir(parents=True, exist_ok=True)
            handoff_path.write_text(handoff_md.rstrip() + "\n", encoding="utf-8")
        else:
            sys.stderr.write("warning: --handoff requested but review JSON had no handoff_markdown\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
