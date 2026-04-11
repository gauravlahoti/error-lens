# Output style guide — open cases

## Result format
Present each open case as a card block — do NOT use markdown tables.
For each case, output this exact format:

---

**#[n] — [severity]**
**Case ID:** `[uuid]`
**Service:** [gcp_service] · **Age:** [human-readable duration]

**Error Summary:**
[error_summary — full text, do not truncate]

---

Repeat for each case, incrementing the number.

## Sorting rules
- Sort by severity first: critical → high → medium → low
- Within the same severity, sort by age descending (oldest first)

## Formatting rules
- Case ID as full UUID in backticks — engineers need it to close cases later
- Do not truncate the error summary
- Age as human-readable duration: "2 hours", "3 days", "1 week"
- Bold the severity label for critical cases

## Summary header
Above the table always include:
"**[N] open case(s)** in the knowledge bank — [X] critical, [Y] high."

Only mention critical and high counts. Omit medium/low from the header.

## No results response
When no open cases exist respond with exactly:
"No open cases in the knowledge bank."
One line. Stop.

## After the cards
Always end with:
"To close a case once your fix is confirmed, share the case ID
and I will record it for your team."
