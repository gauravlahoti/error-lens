# Similarity score guide

## Score interpretation

| Range | Label | Behaviour |
|---|---|---|
| 0.90 – 1.00 | Strong match | Surface confidently as confirmed fix |
| 0.85 – 0.89 | Confident match | Surface with high confidence |
| 0.75 – 0.84 | Borderline match | Surface with a caveat line |
| 0.00 – 0.74 | Weak match | Do not surface — treat as no result |

## Threshold
The confidence threshold is 0.85. Only results at or above this score
should be presented as confirmed fixes.

## Borderline caveat
When the top result scores between 0.75 and 0.84 add this line beneath
the table:
"This match is below the confidence threshold — review carefully before
applying the fix."

## No results
When no results are returned or all scores fall below 0.75 respond with
the exact phrase defined in output_style_guide.md.

## Multiple results
Show up to 3 results. Never show more than 3 regardless of how many
the tool returns. Always order by similarity score descending.