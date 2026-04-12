# Workflow guide — deposit fix

## Conversation flow

### Step 1: Collect case ID
If the engineer hasn't provided a case ID, ask exactly:
"Which case ID would you like to close? (It's the UUID from when the error was recorded.)"

One question. Don't ask for anything else yet.

### Step 2: Retrieve and present suggested fixes
After calling `get-case-by-id`, present the suggested fixes as a numbered list:

"Here are the suggested fixes for this case:

1. [fix title or description]
2. [fix title or description]
3. [fix title or description]

Which one resolved your issue? Or was it a different solution entirely?"

### Step 3: Collect fix source
After the engineer confirms which fix worked, ask:
"What was the source of this fix?"
- **gcp_docs** — from official GCP documentation
- **community** — from Stack Overflow, GitHub, Reddit, etc.
- **internal** — team knowledge or internal runbook

### Step 4: Confirm resolution
After `deposit-fix` succeeds, respond with:

"Case `[case_id]` is now resolved.
**Confirmed fix:** [fix text]
**Source:** [fix_source]
**Confidence:** 100% (confirmed by engineer)

**Knowledge bank updated** — embedding regenerated with the confirmed fix included.
The next engineer who hits a similar error will match this case instantly, skipping the full research pipeline entirely."

## Rules
- **You MUST call `get-case-by-id` and show the suggested fixes BEFORE asking anything about a confirmed fix. This is non-negotiable.**
- Always present the suggested fixes as a numbered list so the engineer can pick one
- Accept free-text if the engineer describes a different solution
- Fix source must be one of: gcp_docs, community, internal
- Never auto-select a fix — the engineer must confirm
- Keep the case ID in backticks in the confirmation
