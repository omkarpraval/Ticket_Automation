# Helix eval results

## Triage accuracy

Skipped: GEMINI_API_KEY not set.

## Retrieval hit@3

Evaluated on 21 held-out resolved incidents with a known duplicate in the corpus.

| Method | hit@3 |
|---|---|
| Vector only | 0.0% |
| Lexical only | 95.2% |
| Fused (RRF) | 95.2% |


## Abstain calibration

Correctly abstained on **5/5** out-of-scope queries.

| Query | Best fused score | Abstained |
|---|---|---|
| What's the best way to plan a surprise birthday party for a  | 0.0 | yes |
| Can someone recommend a good coffee blend for the office kit | 0.0164 | yes |
| I need help renewing my parking permit for the downtown gara | 0.0164 | yes |
| What's the process for submitting a travel expense report fo | 0.0164 | yes |
| One of the chairs in the third floor conference room is wobb | 0.0164 | yes |
