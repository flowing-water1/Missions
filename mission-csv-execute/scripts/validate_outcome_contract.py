#!/usr/bin/env python3
"""Validate a persisted mission Outcome Contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EVIDENCE_LEVELS = {
    "real_e2e",
    "integration",
    "unit",
    "static",
    "human_review",
    "agent_review",
}
ARTIFACT_KINDS = {"design", "plan", "task"}
ROOT_KEYS = {
    "source",
    "execution_scope",
    "artifact_role",
    "desired_effects",
    "reader_questions",
    "decisive_result",
    "blocked_claims",
}


def _require_text(item: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    if not isinstance(item.get(key), str) or not item[key].strip():
        errors.append(f"{label} missing {key}")


def validate_contract(data: Any) -> list[str]:
    if not isinstance(data, dict):
        return ["outcome contract root must be an object"]

    errors: list[str] = []
    for key in sorted(ROOT_KEYS - set(data)):
        errors.append(f"outcome contract missing {key}")
    if errors:
        return errors

    _require_text(data, "source", "outcome contract", errors)
    _require_text(data, "execution_scope", "outcome contract", errors)

    role = data.get("artifact_role")
    if not isinstance(role, dict):
        errors.append("artifact_role must be an object")
    else:
        for key in ("kind", "producer", "authority", "not_authority"):
            _require_text(role, key, "artifact_role", errors)
        if role.get("kind") not in ARTIFACT_KINDS:
            errors.append(f"artifact_role has invalid kind: {role.get('kind')}")
        if not isinstance(role.get("consumers"), list) or not role.get("consumers") or not all(
            isinstance(value, str) and value.strip() for value in role.get("consumers", [])
        ):
            errors.append("artifact_role consumers must be a non-empty string array")

    effects = data.get("desired_effects")
    if not isinstance(effects, list) or not effects:
        errors.append("desired_effects must be a non-empty array")
    else:
        effect_ids: set[str] = set()
        for index, effect in enumerate(effects):
            label = f"desired_effects[{index}]"
            if not isinstance(effect, dict):
                errors.append(f"{label} must be an object")
                continue
            effect_id = effect.get("id")
            if not isinstance(effect_id, str) or not re.fullmatch(r"EFFECT-\d{3}", effect_id):
                errors.append(f"{label} has invalid id")
            elif effect_id in effect_ids:
                errors.append(f"duplicate desired effect id: {effect_id}")
            else:
                effect_ids.add(effect_id)
            for key in ("statement", "source_ref"):
                _require_text(effect, key, label, errors)

    questions = data.get("reader_questions")
    if not isinstance(questions, list) or not questions:
        errors.append("reader_questions must be a non-empty array")
    else:
        question_ids: set[str] = set()
        for index, question in enumerate(questions):
            label = f"reader_questions[{index}]"
            if not isinstance(question, dict):
                errors.append(f"{label} must be an object")
                continue
            question_id = question.get("id")
            if not isinstance(question_id, str) or not re.fullmatch(r"OUTCOME-\d{3}", question_id):
                errors.append(f"{label} has invalid id")
            elif question_id in question_ids:
                errors.append(f"duplicate reader question id: {question_id}")
            else:
                question_ids.add(question_id)
            for key in ("question", "why_it_matters", "scope", "source_ref"):
                _require_text(question, key, label, errors)
            evidence = question.get("evidence_required")
            if evidence not in EVIDENCE_LEVELS:
                errors.append(f"{label} has invalid evidence_required: {evidence}")
            if question.get("status") != "pending":
                errors.append(f"{label} status must be pending")

    decisive = data.get("decisive_result")
    if not isinstance(decisive, dict):
        errors.append("decisive_result must be an object")
    else:
        for key in ("question", "success_condition", "failure_condition"):
            _require_text(decisive, key, "decisive_result", errors)
        if not isinstance(decisive.get("source_refs"), list) or not decisive.get("source_refs") or not all(
            isinstance(value, str) and value.strip() for value in decisive.get("source_refs", [])
        ):
            errors.append("decisive_result source_refs must be a non-empty string array")

    blocked = data.get("blocked_claims")
    if not isinstance(blocked, list):
        errors.append("blocked_claims must be an array")
    else:
        for index, claim in enumerate(blocked):
            label = f"blocked_claims[{index}]"
            if not isinstance(claim, dict):
                errors.append(f"{label} must be an object")
                continue
            for key in ("claim", "reason", "release_condition", "source_ref"):
                _require_text(claim, key, label, errors)
    return errors


def load_contract(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.is_file():
        return None, [f"outcome contract does not exist: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"outcome contract is not valid JSON: {path}: {exc}"]
    errors = validate_contract(data)
    return data if isinstance(data, dict) else None, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    args = parser.parse_args()

    _, errors = load_contract(Path(args.path).expanduser().resolve())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("outcome_contract_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
