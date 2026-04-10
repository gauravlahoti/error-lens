# Output style guide — search errors

## Result table format
Always present results in this exact column order:

| # | Similarity | Service | Severity | Confirmed fix | Case ID |
|---|---|---|---|---|---|
| 1 | 98% match | Cloud Run | high | Grant roles/iam.serviceAccountUser... | KB-0042 |

## Formatting rules
- Convert raw score to percentage: 0.98 → 98% match
- Bold the top result row when similarity >= 0.85
- Show case ID in every row — engineers need it to close cases later
- Truncate confirmed fix text to 60 characters followed by ...
- Never show raw UUID in the table — use KB-XXXX short form if available

## Confidence header
Above the table always include one line:

For strong or confident match (>= 0.85):
"Found [N] similar resolved case(s) in your knowledge bank."

For borderline match (0.75 – 0.84):
"Found a potential match below the confidence threshold — review before applying."

## No results response
When nothing is found respond with exactly:
"No similar resolved cases found in your knowledge bank."
Do not add suggestions, apologies, or offers to search differently.
One line. Stop.

## After the table
Always end with:
"To close a case once your fix is confirmed, share the case ID
and I will record it for your team."