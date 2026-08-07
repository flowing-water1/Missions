# Outcome Contract

Outcome Contract records what a human must be able to decide after a mission finishes. It is
separate from the claim ledger: claims describe implementation promises; outcomes describe the
questions the final evidence and handoff must answer.

## File And Ownership

- File: `<task-stem>.outcomes.json`, next to the mission CSV.
- Producer: `mission-approved-doc` for canonical specs. Compatibility CSVs may omit this sidecar.
- Consumers: mission vision review, human handoff, and domain reports such as Langfuse eval reports.
- CSV reference: add `outcome_contract:<task-stem>.outcomes.json` to relevant issue and REVIEW notes.
- Lifecycle: freeze before execution. Do not write runtime answers back into this file.

## Schema

```json
{
  "source": "docs/spec.md or original request",
  "execution_scope": "approved scope",
  "artifact_role": {
    "kind": "design | plan | task",
    "producer": "who authored the source",
    "consumers": ["mission review", "handoff"],
    "authority": "what the source controls",
    "not_authority": "what the source cannot prove"
  },
  "desired_effects": [
    {
      "id": "EFFECT-001",
      "statement": "user or product behavior after success",
      "source_ref": "path:line or original-request"
    }
  ],
  "reader_questions": [
    {
      "id": "OUTCOME-001",
      "question": "one falsifiable decision question",
      "why_it_matters": "why the user needs this answer",
      "evidence_required": "real_e2e | integration | unit | static | human_review",
      "scope": "where the answer applies",
      "source_ref": "path:line or original-request",
      "status": "pending"
    }
  ],
  "decisive_result": {
    "question": "what result decides whether the mission achieved its purpose?",
    "success_condition": "evidence required for success",
    "failure_condition": "evidence that means failure or an evidence gap",
    "source_refs": ["path:line"]
  },
  "blocked_claims": [
    {
      "claim": "what cannot currently be claimed",
      "reason": "why not",
      "release_condition": "what evidence would allow the claim",
      "source_ref": "path:line or original-request"
    }
  ]
}
```

## Extraction Rules

1. Extract from the approved source or original task, not from model familiarity.
2. Use the current conversation only as a supplementary source when it is still available and does
   not conflict with the approved source. Persist any such question with `source_ref=original-request`.
3. Keep questions decision-relevant, falsifiable, evidence-backed, and scoped.
4. Do not include temporary terminology questions, file-location questions, or unrelated discussion.
5. Do not include benchmark expected answers, answer hints, or target-specific prompt content.
6. Do not pre-fill pass/fail. Every reader question starts with `status=pending`.

## Review Answers

Vision review returns one `outcome_answers` entry per reader question:

```json
{
  "question_id": "OUTCOME-001",
  "verdict": "pass | fail | partial | unknown | not_run",
  "answer": "direct answer",
  "evidence_refs": ["trace/test/artifact reference"],
  "confidence": "high | moderate | low | unknown",
  "boundary": "what this evidence cannot establish",
  "next_action": "how to resolve fail, partial, unknown, or not_run"
}
```

The handoff renders these answers for humans without exposing `OUTCOME-*` ids. It must distinguish
implementation status, validation status, and capability verdict.

The reader-question answer table and blocked-claim table are mechanically derived fields. Keep the
question, verdict, answer, evidence refs joined by `; `, confidence, boundary, next action, claim,
reason, and release condition byte-for-byte equal to the structured JSON/Outcome Contract. Apply
`humanizer-zh` only to prose outside these tables.
