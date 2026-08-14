# Helix eval results

## Triage accuracy

Exact-match category accuracy: **0.0%** (25 held-out incidents).

| Incident | True category | Predicted |
|---|---|---|
| INC-0302 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0255 | Printers & Devices | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0125 | Laptop / Endpoint | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0160 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0208 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0182 | Access Management | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0183 | Printers & Devices | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0083 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0224 | ERP / WMS | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0086 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0252 | Access Management | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0289 | Security | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0049 | Telephony | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0042 | Email & Collaboration | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0041 | ERP / WMS | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0087 | Email & Collaboration | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0277 | Security | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0139 | Email & Collaboration | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0211 | Email & Collaboration | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0031 | Network & VPN | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0163 | Email & Collaboration | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0192 | ERP / WMS | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0223 | Telephony | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0165 | Laptop / Endpoint | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |
| INC-0250 | Laptop / Endpoint | ERROR: ('RATE_LIMITED', 'The AI provider is rate-limiting requests. Try again shortly.', 429) |

## Retrieval hit@3

Evaluated on 23 held-out resolved incidents with a known duplicate in the corpus.

| Method | hit@3 |
|---|---|
| Vector only | 8.7% |
| Lexical only | 100.0% |
| Fused (RRF) | 82.6% |

Note: fused did **not** beat both individual methods on this run - reported honestly rather than adjusted.

## Abstain calibration

Correctly abstained on **4/5** out-of-scope queries.

| Query | Best fused score | Abstained |
|---|---|---|
| What's the best way to plan a surprise birthday party for a  | 0.0164 | yes |
| Can someone recommend a good coffee blend for the office kit | 0.0164 | yes |
| I need help renewing my parking permit for the downtown gara | 0.0308 | no |
| What's the process for submitting a travel expense report fo | 0.0164 | yes |
| One of the chairs in the third floor conference room is wobb | 0.0164 | yes |
