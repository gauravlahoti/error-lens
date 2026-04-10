---
name: search-errors
description: Search the error knowledge bank for similar past GCP errors and confirmed resolutions. Use when a developer shares an error message, stack trace, log snippet, or asks about a past case.
---

# Search errors

## When to use
When any error message, exception, stack trace, or GCP issue is shared.

## Tools you may use in this skill
- `search-similar-errors` — the only tool you may call for this skill
- `load_skill_resource` — only to load reference files listed below

## Steps
1. **FIRST** — call `load_skill_resource` with skill_name=`search-errors` and path=`references/similarity_guide.md`. Read the full content before doing anything else. Do NOT skip this step.
2. Call `load_skill_resource` with skill_name=`search-errors` and path=`references/output_style_guide.md`. Read the full content before continuing. Do NOT skip this step.
3. Combine the error text and GCP service name into a single search query.
4. Call `search-similar-errors` tool with the combined query.
5. Using the similarity guide, classify each result's score and discard any below 0.75.
6. Using the output style guide, format your final response exactly as specified — table format, confidence header, and closing line. Do not deviate from the guide.

## Available references (loaded in steps 1–2)
- `references/similarity_guide.md` — how to interpret similarity scores
  and decide whether a match is confident enough to surface
- `references/output_style_guide.md` — how to format and present results

## Important
Never call `record-new-error` automatically after a failed search.
If no results — respond exactly as `output_style_guide.md` instructs and stop.