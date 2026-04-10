---
name: log-error
description: Record a new error case into the knowledge bank. Use when explicitly asked to log, record, or save a new error with all required fields provided — error message, summary, service, severity, root cause, suggested fixes, and confidence.
---

# Log a new error

## When to use
When explicitly asked to record, log, or save a new error into the
knowledge bank AND all required fields are provided in the request.

## Tools you may use in this skill
- `record-new-error` — records the error case into AlloyDB
- `load_skill_resource` — only to load reference files listed below

## Steps
1. **FIRST** — call `load_skill_resource` with skill_name=`log-error` and path=`references/field_guide.md`. Read the full content before doing anything else. Do NOT skip this step.
2. Validate that ALL required fields are present in the request.
3. If any required field is missing, respond with exactly what's missing — do not guess or fill in defaults.
4. Call `record-new-error` with all required fields.
5. Format the confirmation using the field guide's response template.

## Available references (loaded in step 1)
- `references/field_guide.md` — required fields, validation rules, and response format

## Important
- NEVER call `record-new-error` automatically after a failed search — only when explicitly asked.
- NEVER ask the user for fields to record — that is handled by the orchestrating agent upstream.
- The `id` returned by `record-new-error` is a UUID from AlloyDB — always copy it verbatim.
- NEVER invent, abbreviate, or reformat the case_id.
