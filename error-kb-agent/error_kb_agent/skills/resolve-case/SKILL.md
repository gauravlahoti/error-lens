---
name: resolve-case
description: Resolve an error case with a confirmed fix. Use when an engineer says a fix worked, wants to close a case, or wants to record a verified resolution into the knowledge bank.
---

# Resolve a case

## When to use
When an engineer confirms a fix resolved their issue, wants to close
a case, or wants to record what worked.

## Tools you may use in this skill
- `get-case-by-id` — retrieves full case details including suggested fixes
- `deposit-fix` — deposits the confirmed fix and closes the case
- `load_skill_resource` — only to load reference files listed below

## Steps
1. **FIRST** — call `load_skill_resource` with skill_name=`resolve-case` and path=`references/workflow_guide.md`. Read the full content before doing anything else. Do NOT skip this step.
2. If the engineer has not provided a case ID, ask for it once.
3. **MANDATORY** — As soon as you have a case ID, call `get-case-by-id` IMMEDIATELY. You MUST do this BEFORE asking ANY questions about fixes. The engineer needs to SEE the suggested fixes from the database before they can tell you which one worked. Do NOT ask "what fix did you use?" or "please provide the confirmed fix" without first calling this tool and showing the results.
4. Present the suggested fixes as a numbered list and ask which one resolved the issue, or whether it was a different solution entirely.
5. Ask for the fix source — `gcp_docs`, `community`, or `internal`.
6. Call `deposit-fix` with the case ID, confirmed fix text, and fix source.
7. Confirm the case is now resolved using the format from the workflow guide. Note that confidence is now 100% since the fix is confirmed.

## Available references (loaded in step 1)
- `references/workflow_guide.md` — conversation flow and response formatting

## Important
- Never skip asking which fix resolved the issue — the engineer must confirm.
- Never invent a case ID or fix source — always get them from the engineer.
- The case ID is a UUID from AlloyDB — render it exactly as received.
