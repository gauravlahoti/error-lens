# Output style guide — search errors

## Result format
Present each result as a card block — do NOT use markdown tables.
For each match, output this exact format:

---

**#1 — [similarity]% match**
**Service:** [gcp_service] · **Severity:** [severity]
**Case ID:** `[case_id]`

**Confirmed Fix:**
[confirmed_fix — full text, do not truncate]

---

Repeat for each result, incrementing the number.

## Formatting rules
- Convert raw score to percentage: 0.98 → 98%
- Show case ID in every card — engineers need it to close cases later
- Use the full UUID as the case ID (e.g. `8a837b8e-d76d-4596-adb1-edd2194a046d`)
- Do not abbreviate or shorten the case ID

## Confidence header
Above the cards always include one line:

For strong or confident match (>= 0.85):
"Found [N] similar resolved case(s) in your knowledge bank."

For borderline match (0.75 – 0.84):
"Found a potential match below the confidence threshold — review before applying."

## No results response
When nothing is found respond with exactly:
"No similar resolved cases found in your knowledge bank."
Do not add suggestions, apologies, or offers to search differently.
One line. Stop.

## After the cards
Always end with:
"To close a case once your fix is confirmed, share the case ID
and I will record it for your team."