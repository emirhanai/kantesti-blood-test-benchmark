# Kantesti AI Engine (2.78T) — Blood Test Benchmark V11

**Run:** 2026-04-23 21:50:54  
**Version:** V11  
**Engine:** `Kantesti AI Engine (2.78T)`  
**Cases:** 15/15 scored  
**Composite Score:** `0.9912` (`99.12%`)  

## Aggregate Metrics

| Metric | Value |
|---|---|
| Composite | **0.9912** |
| Structural | 0.998 |
| Clinical | 0.998 |
| Avg Latency | 20.17 s |
| Min Latency | 17.0 s |
| Max Latency | 37.0 s |

## Per-Category Breakdown

| Category | Cases | Composite | Structural | Clinical |
|---|---:|---:|---:|---:|
| Hematology | 3 | 1.000 | 1.000 | 1.000 |
| Endocrinology | 3 | 0.979 | 0.988 | 1.000 |
| Metabolic | 2 | 1.000 | 1.000 | 1.000 |
| Hepatology | 2 | 0.975 | 1.000 | 1.000 |
| Trap | 2 | 1.000 | 1.000 | 1.000 |
| Nephrology | 1 | 1.000 | 1.000 | 1.000 |
| Cardiology | 1 | 1.000 | 1.000 | 1.000 |
| Rheumatology | 1 | 0.981 | 1.000 | 0.965 |

## Per-Case Results

| # | Case ID | Title | Category | Composite | Structural | Clinical | Latency | Path |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | BT-001-IDA | Iron Deficiency Anemia — 34F | Hematology | **1.000** | 1.000 | 1.000 | 17.8s | primary |
| 2 | BT-006-B12 | Vitamin B12 Deficiency / Megaloblastic Anemia — 68F | Hematology | **1.000** | 1.000 | 1.000 | 18.4s | primary |
| 3 | BT-007-THAL | β-Thalassemia Minor — 28M | Hematology | **1.000** | 1.000 | 1.000 | 17.0s | primary |
| 4 | BT-002-HASH | Hashimoto's Thyroiditis — 42F | Endocrinology | **0.950** | 1.000 | 1.000 | 37.0s | fallback |
| 5 | BT-008-PCOS | PCOS with Insulin Resistance — 26F | Endocrinology | **0.987** | 0.963 | 1.000 | 18.6s | primary |
| 6 | BT-003-T2DM | T2DM + Metabolic Syndrome — 51M | Metabolic | **1.000** | 1.000 | 1.000 | 19.1s | primary |
| 7 | BT-013-GOUT | Hyperuricemia with Gout Risk — 48M | Metabolic | **1.000** | 1.000 | 1.000 | 19.4s | primary |
| 8 | BT-004-NAFLD | NAFLD / NASH — 46M | Hepatology | **1.000** | 1.000 | 1.000 | 19.6s | primary |
| 9 | BT-009-VIRHEP | Acute Viral Hepatitis — 22M | Hepatology | **0.950** | 1.000 | 1.000 | 23.4s | fallback |
| 10 | BT-014-GILBERT | Gilbert's Syndrome — Isolated Unconjugated Hyperbilirubinemia [Trap] — 24M | Trap | **1.000** | 1.000 | 1.000 | 18.9s | primary |
| 11 | BT-005-CKD | CKD Stage 3 — 62M | Nephrology | **1.000** | 1.000 | 1.000 | 17.4s | primary |
| 12 | BT-010-ASCVD | High Cardiovascular Risk — Atherogenic Dyslipidemia — 58M | Cardiology | **1.000** | 1.000 | 1.000 | 19.7s | primary |
| 13 | BT-011-SLE | Systemic Lupus Erythematosus — 31F | Rheumatology | **0.981** | 1.000 | 0.965 | 18.2s | primary |
| 14 | BT-012-VITD | Severe Vitamin D Deficiency + Secondary Hyperparathyroidism — 55F | Endocrinology | **1.000** | 1.000 | 1.000 | 19.3s | primary |
| 15 | BT-015-HEALTHY | Healthy Adult — Routine Screening [Trap] — 35F | Trap | **1.000** | 1.000 | 1.000 | 18.7s | fallback |

## Methodology

Scores are computed against a **pre-registered rubric** — the expected diagnoses, clinical scoring systems and report sections are fixed before the engine is invoked, so no cherry-picking is possible after the fact.

Composite = `0.35 × Structural + 0.55 × Clinical + 0.10 × Latency`.

**Structural (35%)** — fraction of the 7 mandatory report sections and 16 mandatory subsections present in the output, weighted 40/60.

**Clinical (55%)** — diagnosis keyword recall (70%), scoring-system recall (20%), probability sum in [90,110] (10%). Trap cases carry a hyperdiagnosis penalty of up to 0.30 for fabricated pathologies.

**Latency (10%)** — 0.10 if <20 s (primary-path target), 0.05 if <40 s (soft ceiling), 0 otherwise.

## Case Reference

| Case ID | Category | Rationale |
|---|---|---|
| BT-001-IDA | Hematology | Microcytic-hypochromic anemia with depleted ferritin, low TSAT, high TIBC — textbook absolute iron deficiency. Mentzer Index (MCV/RBC) should be >13, supporting IDA over thalassemia. |
| BT-006-B12 | Hematology | Macrocytic anemia (MCV 112) with low B12, elevated MMA and homocysteine — classic cobalamin deficiency. Elevated LDH and indirect bilirubin reflect ineffective erythropoiesis. Differential should flag pernicious anemia in a 68-year-old. |
| BT-007-THAL | Hematology | Differentiator case: microcytosis with HIGH RBC count, normal RDW, normal ferritin and elevated HbA2 (>3.5%) — β-thalassemia trait, NOT iron deficiency. Mentzer Index = 65.8/6.2 ≈ 10.6 (<13 points to thalassemia). Tests whether the engine uses Mentzer correctly instead of defaulting to IDA. |
| BT-002-HASH | Endocrinology | Overt primary hypothyroidism (TSH 18.4, low FT4/FT3) with strongly positive anti-TPO and anti-Tg — Hashimoto's thyroiditis. Secondary dyslipidemia expected. |
| BT-008-PCOS | Endocrinology | Rotterdam-style PCOS picture: elevated LH/FSH ratio (~3.1), biochemical hyperandrogenism (high total+free testosterone, low SHBG), elevated AMH. HOMA-IR ≈ 4.97 (insulin 21 × glucose 96 / 405) indicates meaningful insulin resistance despite normoglycemia. |
| BT-003-T2DM | Metabolic | ADA-criteria T2DM (HbA1c 7.8%, FPG 142) with atherogenic dyslipidemia, low HDL, hepatic transaminase elevation — meets ≥3 NCEP-ATP III criteria for metabolic syndrome. HOMA-IR ≈ 7.7. |
| BT-013-GOUT | Metabolic | Uric acid 9.8 with elevated inflammatory markers (ESR/CRP) and metabolic co-factors (IFG, hypertriglyceridemia) — classic profile for gout in the context of metabolic syndrome. Engine should recommend 24-hour urate excretion to differentiate under-excretion vs over-production. |
| BT-004-NAFLD | Hepatology | ALT-dominant transaminase elevation (De Ritis <1), GGT/ALP cholestasis pattern, hypertriglyceridemia — NAFLD/NASH spectrum. FIB-4 should be computed to stratify advanced fibrosis risk. |
| BT-009-VIRHEP | Hepatology | Extreme hepatocellular injury (ALT 1420, AST 980; ratio <1 = hepatocellular), conjugated hyperbilirubinemia, mild coagulopathy (INR 1.3), relative lymphocytosis — strongly suggests acute viral hepatitis. Engine should recommend urgent HAV/HBV/HCV/HEV serology and abdominal imaging. |
| BT-014-GILBERT | Trap | TRAP CASE. Isolated indirect hyperbilirubinemia with fully normal LFTs, preserved haptoglobin and LDH, normal reticulocytes — rules out hemolysis AND hepatocellular injury. Correct diagnosis: Gilbert's syndrome (UGT1A1 polymorphism, benign). Penalises engines that over-diagnose hepatitis or hemolytic anemia on isolated bilirubin elevation. |
| BT-005-CKD | Nephrology | eGFR 38 + UACR 120 places the patient in KDIGO G3b/A2 — CKD Stage 3. Early features of CKD-MBD (borderline phosphate) and renal anemia. Nephrology referral warranted. |
| BT-010-ASCVD | Cardiology | Severely elevated atherogenic particles (ApoB 148, non-HDL 236, Lp(a) 96), low HDL, high-sensitivity CRP >3 — high ASCVD 10-year risk category. Engine should recommend statin (high-intensity), lifestyle overhaul, and consider Lp(a)-targeted discussion. |
| BT-011-SLE | Rheumatology | Multi-system autoimmune picture meeting 2019 EULAR/ACR SLE criteria: ANA 1:640, high anti-dsDNA and anti-Smith (SLE-specific), low C3/C4, lymphopenia, thrombocytopenia, and nephrotic-range proteinuria — concerning for lupus nephritis. Engine should recommend urgent rheumatology + nephrology referral and renal biopsy. |
| BT-012-VITD | Endocrinology | 25-OH-D 11 (severe deficiency) with compensatory PTH elevation (98), low-normal calcium and phosphorus, elevated ALP — classic picture of secondary hyperparathyroidism from vitamin D deficiency. Bone-mineral implications warrant DEXA and repletion protocol. |
| BT-015-HEALTHY | Trap | TRAP CASE. Every parameter sits comfortably within its reference range. Correct output: reassurance + lifestyle maintenance. Penalises engines that manufacture borderline pathologies to sound clinically useful. |

---
*Generated by Kantesti AI Engine (2.78T) Benchmark Harness V11.*
