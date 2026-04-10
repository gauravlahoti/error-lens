# Output style guide — open cases

## Table format
Always present open cases in this exact column order:

| # | Case ID | Service | Severity | Error Summary | Age |
|:---:|---|---|:---:|---|:---:|
| 1 | `uuid` | Cloud Run | critical | Connection pool exhausted... | 3 days |

Column alignment: # center, Severity center, Age center. All others left-aligned.

## Sorting rules
- Sort by severity first: critical → high → medium → low
- Within the same severity, sort by age descending (oldest first)

## Formatting rules
- Case ID in backticks — engineers need it to close cases later
- Truncate error summary to 50 characters followed by ...
- Age as human-readable duration: "2 hours", "3 days", "1 week"
- Bold any row with critical severity

## Summary header
Above the table always include:
"**[N] open case(s)** in the knowledge bank — [X] critical, [Y] high."

Only mention critical and high counts. Omit medium/low from the header.

## No results response
When no open cases exist respond with exactly:
"No open cases in the knowledge bank."
One line. Stop.

## After the table
Always end with:
"To close a case once your fix is confirmed, share the case ID
and I will record it for your team."
