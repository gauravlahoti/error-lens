---
name: open-cases
description: List all unresolved error cases from the knowledge bank. Use when a developer asks about open cases, pending issues, unresolved errors, or wants to see what needs attention.
---

# Open cases

## When to use
When a developer asks about open cases, pending issues, unresolved errors,
case backlog, or what needs attention.

## Tools you may use in this skill
- `get-open-cases` — retrieves all unresolved cases from the knowledge bank
- `load_skill_resource` — only to load reference files listed below

## Steps
1. **FIRST** — call `load_skill_resource` with skill_name=`open-cases` and path=`references/output_style_guide.md`. Read the full content before doing anything else. Do NOT skip this step.
2. Call `get-open-cases` to retrieve the list of unresolved cases.
3. Format the results following the output style guide EXACTLY — use the table format, sorting rules, summary header, and closing line from the guide. Do not use any other format.

## Available references (loaded in step 1)
- `references/output_style_guide.md` — how to format and present the open cases list

## Important
- Never modify, close, or record cases in this skill — only list them.
- If no open cases are found, respond: "No open cases in the knowledge bank."
