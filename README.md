<p align="center">
  <a href="https://www.kantesti.net">
    <img src="https://www.kantesti.net/storage/2026/02/kantesti-smart-health-ai-diagnostics-identity.webp" alt="Kantesti — Smart Health AI Diagnostics" width="640">
  </a>
</p>

<h1 align="center">Kantesti AI Engine (2.78T) — Blood Test Benchmark V11</h1>

<p align="center">
  <a href="https://doi.org/10.6084/m9.figshare.32095435"><img src="https://img.shields.io/badge/DOI-10.6084%2Fm9.figshare.32095435-blue" alt="DOI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/composite-99.12%25-brightgreen" alt="Composite Score"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/cases-15%2F15-success" alt="Cases"></a>
</p>

A **pre-registered, rubric-based clinical benchmark** of the [Kantesti AI Engine (2.78T)](https://www.kantesti.net) on 15 anonymised blood test cases across seven medical specialties, including two hyperdiagnosis trap cases.

> The harness in this repository is released under the MIT licence. The Kantesti AI Engine itself is a commercial product accessed through its public production API.

---

## Headline result

On a rubric frozen in source code before the first engine invocation, the Kantesti AI Engine (2.78T) achieved:

| Metric | Value |
|---|---|
| **Composite score** | **0.9912 (99.12%)** |
| Structural score | 0.998 |
| Clinical score | 0.998 |
| Avg. latency | 20.17 s |
| Cases scored | 15 / 15 |
| Trap-case false-positives | 0 / 13 monitored flags |

The β-thalassaemia minor case was correctly differentiated from iron deficiency anaemia using the Mentzer index. Both trap cases (Gilbert's syndrome and a fully normal adult screen) returned zero hyperdiagnosis flags.

---

## Why this benchmark matters

AI-assisted blood test interpretation is increasingly used in consumer and clinical workflows, but reproducible evaluation frameworks tailored to laboratory medicine remain uncommon. General-purpose medical QA benchmarks miss the specific failure modes that matter in this setting:

- Can an engine separate iron deficiency from thalassaemia trait when MCV is identical?
- Does it over-diagnose Gilbert's syndrome as hepatitis?
- Does it manufacture pathology in a fully normal screening panel?

This benchmark targets exactly those failure modes, with an explicit hyperdiagnosis penalty on trap cases.

---

## Methodology summary

The composite score for each case is computed as:

```
C = 0.35 × Structural + 0.55 × Clinical + 0.10 × Latency
```

- **Structural (35%)** — fraction of 7 mandatory report sections and 16 mandatory subsections present in the engine output.
- **Clinical (55%)** — diagnosis keyword recall (70%), scoring-system recall (20%), probability-sum validity in [90, 110] (10%). Trap cases carry a hyperdiagnosis penalty of up to 0.30.
- **Latency (10%)** — 0.10 if response under 20 s, 0.05 if under 40 s, otherwise 0.

The full rubric is implemented in [`benchmark_bloodtest.py`](benchmark_bloodtest.py) and was committed before the first engine call. See [`Kantesti_AI_Engine_2.78T_Blood_Test_Benchmark_V11_Technical_Report.pdf`](Kantesti_AI_Engine_2.78T_Blood_Test_Benchmark_V11_Technical_Report.pdf) for the complete methodology, ethics statement, and discussion.

---

## Case coverage

| Specialty | Cases | Representative presentations |
|---|---:|---|
| Hematology | 3 | Iron deficiency anaemia; β-thalassaemia minor; B12 deficiency |
| Endocrinology | 3 | Hashimoto's thyroiditis; PCOS with insulin resistance; vitamin D deficiency |
| Metabolic | 2 | T2DM with metabolic syndrome; hyperuricaemia |
| Hepatology | 2 | NAFLD/NASH; acute viral hepatitis |
| Nephrology | 1 | CKD stage 3 |
| Cardiology | 1 | Atherogenic dyslipidaemia (high ASCVD risk) |
| Rheumatology | 1 | Systemic lupus erythematosus with nephritic features |
| Trap (over-diagnosis) | 2 | Gilbert's syndrome; fully normal adult screen |

---

## How to reproduce

### 1. Clone

```bash
git clone https://github.com/emirhanai/kantesti-blood-test-benchmark.git
cd kantesti-blood-test-benchmark
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Requires Python 3.10 or later.

### 3. Configure Kantesti API credentials

You need a Kantesti API credential pair. Set them as environment variables:

```bash
export KANTESTI_USERNAME="your_username"
export KANTESTI_PASSWORD="your_password"
```

Credentials are read at runtime; nothing is hard-coded in the script.

### 4. Run the benchmark

```bash
python benchmark_bloodtest.py
```

Each run emits four artefacts into the working directory:

- `kantesti_benchmark_<timestamp>_v11.json` — aggregated scorecard
- `kantesti_benchmark_<timestamp>_v11_full.json` — full dump including raw engine responses
- `kantesti_benchmark_<timestamp>_v11.md` — human-readable Markdown report
- `kantesti_benchmark_<timestamp>_v11.csv` — per-case CSV for downstream analysis

The reference run from 23 April 2026 is preserved under [`results/`](results/).

---

## Results from the April 2026 reference run

| # | Case ID | Category | Composite | Structural | Clinical | Latency | Path |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | BT-001-IDA | Hematology | **1.000** | 1.000 | 1.000 | 17.8 s | primary |
| 2 | BT-006-B12 | Hematology | **1.000** | 1.000 | 1.000 | 18.4 s | primary |
| 3 | BT-007-THAL | Hematology | **1.000** | 1.000 | 1.000 | 17.0 s | primary |
| 4 | BT-002-HASH | Endocrinology | **0.950** | 1.000 | 1.000 | 37.0 s | fallback |
| 5 | BT-008-PCOS | Endocrinology | **0.987** | 0.963 | 1.000 | 18.6 s | primary |
| 6 | BT-003-T2DM | Metabolic | **1.000** | 1.000 | 1.000 | 19.1 s | primary |
| 7 | BT-013-GOUT | Metabolic | **1.000** | 1.000 | 1.000 | 19.4 s | primary |
| 8 | BT-004-NAFLD | Hepatology | **1.000** | 1.000 | 1.000 | 19.6 s | primary |
| 9 | BT-009-VIRHEP | Hepatology | **0.950** | 1.000 | 1.000 | 23.4 s | fallback |
| 10 | BT-014-GILBERT | Trap | **1.000** | 1.000 | 1.000 | 18.9 s | primary |
| 11 | BT-005-CKD | Nephrology | **1.000** | 1.000 | 1.000 | 17.4 s | primary |
| 12 | BT-010-ASCVD | Cardiology | **1.000** | 1.000 | 1.000 | 19.7 s | primary |
| 13 | BT-011-SLE | Rheumatology | **0.981** | 1.000 | 0.965 | 18.2 s | primary |
| 14 | BT-012-VITD | Endocrinology | **1.000** | 1.000 | 1.000 | 19.3 s | primary |
| 15 | BT-015-HEALTHY | Trap | **1.000** | 1.000 | 1.000 | 18.7 s | fallback |

Full per-case raw engine outputs are available in [`results/kantesti_benchmark_20260423_220014_v11_full.json`](results/kantesti_benchmark_20260423_220014_v11_full.json).

---

## Repository layout

```
kantesti-blood-test-benchmark/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── benchmark_bloodtest.py
├── Kantesti_AI_Engine_2.78T_Blood_Test_Benchmark_V11_Technical_Report.pdf
└── results/
    ├── kantesti_benchmark_20260423_220014_v11.csv
    ├── kantesti_benchmark_20260423_220014_v11.json
    ├── kantesti_benchmark_20260423_220014_v11_full.json
    └── kantesti_benchmark_20260423_220014_v11.md
```

---

## Data and ethics

The 15 cases evaluated in this study are **anonymised real patient records** drawn from the Kantesti clinical data repository under written informed consent. De-identification was performed under the Safe Harbor approach: all direct identifiers were removed or replaced. Processing was carried out in accordance with **GDPR Article 9(2)(j)** and the equivalent UK GDPR provisions.

No personally identifying information appears in this repository, in the released datasets, or in the technical report.

---

## Limitations

- **Sample size.** 15 cases across 8 specialty buckets is enough for a proof of concept but not for subgroup analysis.
- **Single-shot evaluation.** Each case is evaluated once. A multi-run protocol with reported variance is planned.
- **Single engine.** This report characterises one engine; comparative analyses against alternative systems are out of scope here.
- **Single repository.** Cases are drawn from a single clinical data source; multi-centre extension is on the roadmap.

A planned follow-up adds n = 50 cases, multi-language parity (Turkish, German, Spanish, French, Arabic), and per-case variance over n = 5 runs.

---

## Citation

If you use this benchmark or its data, please cite:

```bibtex
@techreport{klein2026kantesti,
  author      = {Klein, Thomas and Bulut, Julian Emirhan},
  title       = {Clinical Validation of the Kantesti AI Engine (2.78T) on 15 Anonymised Blood Test Cases:
                 A Pre-Registered, Rubric-Based Benchmark Including Hyperdiagnosis Trap Cases
                 Across Seven Medical Specialties},
  institution = {Kantesti Ltd},
  address     = {London, United Kingdom},
  year        = {2026},
  month       = {April},
  type        = {Technical Report},
  number      = {V11},
  doi         = {10.6084/m9.figshare.32095435},
  url         = {https://doi.org/10.6084/m9.figshare.32095435}
}
```

A `CITATION.cff` file is provided so that GitHub will render a "Cite this repository" button automatically.

---

## Related links

- **Figshare (DOI):** <https://doi.org/10.6084/m9.figshare.32095435>
- **ResearchGate:** [Publication 404175463](https://www.researchgate.net/publication/404175463_Clinical_Validation_of_the_Kantesti_AI_Engine_278T_on_15_Anonymised_Blood_Test_Cases_A_Pre-Registered_Rubric-Based_Benchmark_Including_Hyperdiagnosis_Trap_Cases_Across_Seven_Medical_Specialties)
- **Academia.edu:** [Paper 165956808](https://www.academia.edu/165956808/Clinical_Validation_of_the_Kantesti_AI_Engine_2_78T_on_15_Anonymised_Blood_Test_Cases_A_Pre_Registered_Rubric_Based_Benchmark_Including_Hyperdiagnosis_Trap_Cases_Across_Seven_Medical_Specialties)
- **Kantesti website:** <https://www.kantesti.net>
- **Kantesti API documentation:** <https://www.kantesti.net/docs/en/endpoints/>

---

## Authors

**Thomas Klein, MD** — Chief Medical Officer, Kantesti AI. Board-certified clinical hematologist. ORCID: [0009-0009-1490-1321](https://orcid.org/0009-0009-1490-1321). Email: thomas.klein@kantesti.net.

**Julian Emirhan Bulut** — Senior AI Engineer and CEO, Kantesti Ltd. Email: julian@kantesti.net.

---

## Conflict of interest

Both authors are employed by and hold equity in Kantesti Ltd. The engine under evaluation is a commercial product of the same organisation. We disclose this openly and mitigate the obvious bias by:

1. Fixing the scoring rubric in source code before the first engine call.
2. Publishing the full evaluation harness under the MIT licence so that any independent researcher can reproduce the run.
3. Publishing every raw engine response alongside the aggregated scorecard.

---

## Licence

The benchmark harness, scorecards, and documentation in this repository are released under the [MIT Licence](LICENSE). The Kantesti AI Engine itself is a proprietary commercial product accessed via the public production API at `app.aibloodtestinterpret.com`.

---

<p align="center">
  <em>Kantesti Ltd — Companies House No. 17090423 (England &amp; Wales)<br>
  4 Raven Road, Unit 1c3-1100, London E18 1HB, United Kingdom<br>
  <a href="https://www.kantesti.net">www.kantesti.net</a></em>
</p>
