# Kantesti AI v12 November Update: medical benchmarks

Results of 2026-11-15.

| Benchmark | Questions | Answered | Correct | Accuracy |
|---|---|---|---|---|
| PubMedQA (expert-labelled test) | 500 | 500 | 412 | 82.4% |
| MedCalc-Bench (test) | 1100 | 1100 | 957 | 87.0% |
| MedQA (USMLE, 4 options, test) | 1273 | 1273 | 1208 | 94.89% |
| MedHallu (pqa_labeled, detection) | 1000 | 1000 | 876 | 87.6% |

## MedCalc-Bench (test)

- kind: date (60): 63.33%
- kind: decimal (640): 95.78%
- kind: integer (400): 76.5%

## MedHallu (pqa_labeled, detection)

- difficulty: easy (274): 89.78%
- difficulty: hard (408): 85.54%
- difficulty: medium (318): 88.36%

Method: each question was asked once, with the benchmark's own answer options and context, and scored against the benchmark's answer key. Accuracy is over the answered questions.
