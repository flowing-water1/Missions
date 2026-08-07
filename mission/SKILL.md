---
name: mission
description: Use when a task starts from a canonical mission spec, an existing task CSV, a natural-language mission request, or a recovery request and needs deterministic routing to the matching mission workflow.
---

# Mission

Route mission inputs. Do not perform discussion, mapping, execution, or recovery work inside this skill.

Declare: `使用 mission skill，路由到 <子 skill>。`

## Routing

Check in this order; the first match wins.

1. **Existing CSV file or directory**
   - A file must have the standard 19-column header.
   - For a directory, prefer `<dir>/<dir-name>.csv`; if absent, accept its only CSV. Ask only when several candidates remain.
   - Route to `mission-csv-execute`.
2. **Existing canonical spec**
   - Run `mission-spec/scripts/validate_spec.py <path>`.
   - `status: approved` and committed-clean routes to `mission-approved-doc`.
   - `status: draft` routes to `mission-spec`.
   - Invalid metadata hard-stops; do not infer a route from prose or path names.
3. **Existing Markdown without `mission: spec` frontmatter**
   - Treat it as reference material and route to `mission-spec` for canonicalization and approval.
4. **Empty input or continue/resume wording**
   - Route to `mission-recovery`.
5. **Natural-language request passed to `mission`**
   - Route to `mission-spec`.

Ordinary work with a clear goal and acceptance criteria does not need mission. Execute it directly with an ordinary plan when useful.

## Execution stickiness

Once `mission-csv-execute` owns an unfinished CSV, keep routing subsequent progress, explanation, or continue messages to that same execution. Leave only when the CSV reaches a terminal state or the user explicitly pauses, cancels, or changes the task boundary.

## Sub-skills

| Skill | Owns |
|---|---|
| `mission-spec` | Requirement discussion, canonical draft, explicit approval |
| `mission-approved-doc` | Committed approved spec to `issues/<stem>/` artifacts |
| `mission-csv-execute` | CSV state machine, evidence, review, handoff, commits |
| `mission-recovery` | Locate unfinished CSVs under `issues/` and forward them |

Any valid CSV explicitly supplied by path may execute outside `issues/`. Its artifact root is its parent directory; ignored external artifacts remain local unless already tracked.
