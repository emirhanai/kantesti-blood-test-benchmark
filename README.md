<p align="center">
  <a href="https://www.kantesti.net">
    <img src="https://www.kantesti.net/storage/2026/02/kantesti-smart-health-ai-diagnostics-identity.webp" alt="Kantesti — Smart Health AI Diagnostics" width="640">
  </a>
</p>

<h1 align="center">Kantesti AI Engine (2.78T) — Blood Test Benchmark V12</h1>
<h3 align="center"><em>Second Update — 100,000-Patient Cohort Across 127 Countries</em></h3>

<p align="center">
  <a href="https://doi.org/10.6084/m9.figshare.32095435"><img src="https://img.shields.io/badge/DOI-10.6084%2Fm9.figshare.32095435-blue" alt="DOI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/composite-99.80%25-brightgreen" alt="Composite Score"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/cohort-100%2C000-success" alt="Cohort"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/countries-127-informational" alt="Countries"></a>
</p>

A **pre-registered, rubric-based clinical benchmark** of the [Kantesti AI Engine (2.78T)](https://www.kantesti.net) on **100,000 anonymised blood test cases** drawn from the Kantesti SQL-backed clinical repository, spanning **127 countries** and **75+ languages**. This V12 release is the **second update** of the Kantesti Blood Test Benchmark suite, extending the earlier V11 proof-of-concept (15 cases) to a population-scale evaluation.

> The harness in this repository — including the SQL case loader — is released under the MIT licence. The Kantesti AI Engine itself is a commercial product accessed through its public production API.

---

## Update history

| Release | Date | Cohort | Specialties | Countries | Composite |
|---|---|---:|---:|---:|---:|
| V11 (initial) | 23 Apr 2026 | 15 cases | 7 + 1 trap bucket | single repo | 0.9912 |
| **V12 (second update)** | **26 Apr 2026** | **100,000 cases** | **8** | **127** | **0.9980** |

The V11 release validated the rubric and the engine's behaviour on hand-curated differential-diagnosis pitfalls and hyperdiagnosis traps. The V12 update keeps the rubric **byte-identical** and extends the evaluation to the full anonymised production cohort, sourced through a parameterised SQL query against the Kantesti clinical data warehouse.

---

## Headline result

On the same rubric that was frozen in source code before the V11 run, the Kantesti AI Engine (2.78T) achieved on the V12 100K cohort:

| Metric | V11 (n=15) | **V12 (n=100,000)** |
|---|---:|---:|
| **Composite score** | 0.9912 (99.12%) | **0.9980 (99.80%)** |
| Structural score (mean) | 0.998 | **1.000** |
| Clinical score (mean) | 0.998 | **0.996** |
| Avg. latency | 20.17 s | **13.26 s** |
| Min / max latency | 17.0 / 37.0 s | **9.0 / 16.94 s** |
| Cases scored | 15 / 15 | **100,000 / 100,000** |
| Trap-subset hyperdiagnosis | 0 / 13 flags | **0 / 87,412 flags** |
| Engine path = primary | 12 / 15 | **100,000 / 100,000** |

The latency improvement reflects production engine optimisations between V11 and V12; the rubric, the scoring code, and the API endpoint are unchanged.

A 201-case sample of full raw engine responses is published in [`results/kantesti_benchmark_20260426_200720_full.json`](results/kantesti_benchmark_20260426_200720_full.json) for inspection.

---

## Why this benchmark matters

AI-assisted blood test interpretation is increasingly used in consumer and clinical workflows, but reproducible evaluation frameworks tailored to laboratory medicine remain uncommon. The V12 update answers questions that the V11 proof-of-concept could only gesture at:

- Does the engine maintain near-ceiling performance at population scale, not just on hand-picked illustrative cases?
- Is performance consistent across 127 countries and 75+ languages, or does it degrade outside the engine's primary markets?
- How stable are the structural and clinical scores when measured over tens of thousands of independent invocations?
- Does the hyperdiagnosis penalty hold up at scale — i.e., when there are tens of thousands of opportunities to manufacture pathology rather than just two?

The 100K cohort lets us answer those questions directly.

---

## Methodology summary

The composite score for each case is computed as:

```
C = 0.35 × Structural + 0.55 × Clinical + 0.10 × Latency
```

- **Structural (35%)** — fraction of 7 mandatory report sections and 16 mandatory subsections present in the engine output.
- **Clinical (55%)** — diagnosis keyword recall (70%), scoring-system recall (20%), probability-sum validity in [90, 110] (10%). Trap-subset cases carry a hyperdiagnosis penalty of up to 0.30.
- **Latency (10%)** — 0.10 if response under 20 s, 0.05 if under 40 s, otherwise 0.

The full rubric is implemented in [`benchmark_bloodtest.py`](benchmark_bloodtest.py) and was committed before the first V11 engine call. **The rubric was not modified for V12** — only the case loader was changed, from a Python literal list (V11) to a parameterised SQL query against the Kantesti clinical repository (V12). See [`Kantesti_AI_Engine_2_78T_Blood_Test_Benchmark_V12_Technical_Report.pdf`](Kantesti_AI_Engine_2_78T_Blood_Test_Benchmark_V12_Technical_Report.pdf) for the complete methodology, ethics statement, country breakdown, and discussion.

---

## Cohort coverage

### Specialty distribution (V12, n = 100,000)

| Specialty | Cases | Share |
|---|---:|---:|
| Endocrinology | 23,900 | 23.9% |
| Metabolic medicine | 21,900 | 21.9% |
| Hematology | 15,400 | 15.4% |
| Hepatology | 12,400 | 12.4% |
| Internal medicine (incl. trap subset) | 9,000 | 9.0% |
| Cardiology | 7,500 | 7.5% |
| Rheumatology | 6,000 | 6.0% |
| Nephrology | 4,000 | 4.0% |
| **Total** | **100,000** | **100.0%** |

### Geographic distribution — top 30 countries

| # | Country | Cases | # | Country | Cases | # | Country | Cases |
|---:|---|---:|---:|---|---:|---:|---|---:|
| 1 | United States | 10,500 | 11 | Netherlands | 2,400 | 21 | Australia | 1,200 |
| 2 | Brazil | 9,500 | 12 | Belgium | 2,300 | 22 | Poland | 1,100 |
| 3 | Spain | 9,000 | 13 | Japan | 2,000 | 23 | Czechia | 1,000 |
| 4 | Italy | 8,000 | 14 | Ireland | 1,900 | 24 | Norway | 900 |
| 5 | Germany | 7,800 | 15 | South Korea | 1,700 | 25 | Canada | 900 |
| 6 | France | 7,400 | 16 | Switzerland | 1,500 | 26 | Greece | 850 |
| 7 | Portugal | 5,800 | 17 | Sweden | 1,400 | 27 | Chile | 800 |
| 8 | Türkiye | 3,400 | 18 | Denmark | 1,300 | 28 | Austria | 750 |
| 9 | United Kingdom | 2,900 | 19 | India | 1,300 | 29 | Finland | 700 |
| 10 | Mexico | 2,500 | 20 | Argentina | 1,200 | 30 | Romania | 700 |

**Top 30 subtotal:** 92,700 cases (92.7%). Remaining **97 countries** contribute the long-tail balance of 7,300 cases (≈ 75 cases per country on average).

### Continental rollup

| Region | Cases | Share | Composite (mean) |
|---|---:|---:|---:|
| Europe | 57,700 | 57.7% | 0.998 |
| Americas | 25,400 | 25.4% | 0.998 |
| Asia-Pacific | 6,200 | 6.2% | 0.997 |
| Middle East / Africa (named) | 3,400 | 3.4% | 0.998 |
| Long tail (97 countries) | 7,300 | 7.3% | 0.997 |
| **Total / weighted mean** | **100,000** | **100.0%** | **0.998** |

Performance is statistically indistinguishable across regions — the engine does not show geographic skew at the rubric level.

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

### 3. Configure Kantesti credentials

You need a Kantesti API credential pair **and** read-only credentials for the Kantesti clinical repository (the SQL-backed case store). All four are read at runtime; nothing is hard-coded.

```bash
# Engine API
export KANTESTI_USERNAME="your_api_username"
export KANTESTI_PASSWORD="your_api_password"

# Clinical repository (read-only role)
export KANTESTI_DB_HOST="repo.internal.kantesti.net"
export KANTESTI_DB_PORT="3306"
export KANTESTI_DB_NAME="kantesti_clinical_repo"
export KANTESTI_DB_USER="bench_reader"
export KANTESTI_DB_PASSWORD="your_db_password"
```

The default SQL query — `SELECT ... FROM anonymised_blood_panels WHERE consent_research = 1 LIMIT :limit` — is parameterised and read-only. It is printed at the top of every run.

### 4. Run the benchmark

```bash
# V12 default: 100,000 cases from SQL
python benchmark_bloodtest.py

# Smaller sample (e.g. n = 1,000) for quick iteration
python benchmark_bloodtest.py --limit 1000

# Localise the response language
python benchmark_bloodtest.py --lang tr

# Sandbox mode (no credit consumption)
python benchmark_bloodtest.py --sandbox
```

Each run emits four artefacts into the working directory:

- `kantesti_benchmark_<timestamp>.json` — aggregated scorecard (suite + per-category + per-country)
- `kantesti_benchmark_<timestamp>_full.json` — full dump (sampled raw responses)
- `kantesti_benchmark_<timestamp>.md` — human-readable Markdown report
- `kantesti_benchmark_<timestamp>.csv` — per-case CSV for downstream analysis

The reference V12 run from 26 April 2026 is preserved under [`results/`](results/).

---

## Repository layout

```
kantesti-blood-test-benchmark/
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── benchmark_bloodtest.py
├── Kantesti_AI_Engine_2_78T_Blood_Test_Benchmark_V12_Technical_Report.pdf
├── Kantesti_AI_Engine_2_78T_Blood_Test_Benchmark_V11_Technical_Report.pdf   ← preserved baseline
└── results/
    ├── kantesti_benchmark_20260426_200720.json
    ├── kantesti_benchmark_20260426_200720_full.json   ← sampled raw responses (n=201)
    ├── kantesti_benchmark_20260426_200720.md
    ├── kantesti_benchmark_20260426_200720.csv
    └── (V11 baseline files preserved alongside)
```

---

## Data and ethics

The 100,000 cases evaluated in V12 are **anonymised real patient records** drawn from the Kantesti SQL-backed clinical data repository under written informed consent. De-identification is performed at write-time under the Safe Harbor approach: all direct identifiers are removed or replaced before any record reaches the benchmark loader. The benchmark loader queries the repository through a **read-only role** that has no access to identifying tables; the schema enforces this at the database level, not just in application code.

Processing was carried out in accordance with **GDPR Article 9(2)(j)** and the equivalent UK GDPR provisions. Country information retained in the released artefacts is at the **ISO 3166-1 alpha-2 level only** (e.g. `DE`, `BR`); no sub-national identifiers, postal codes, or facility identifiers appear anywhere in the public release.

No personally identifying information appears in this repository, in the released datasets, or in the technical report.

---

## Limitations

- **Single engine.** This report characterises one engine; comparative analyses against alternative systems are out of scope here.
- **Single-shot evaluation.** Each of the 100K cases is evaluated once. A multi-run protocol with reported per-case variance is planned for V13.
- **Sample-of-sample disclosure.** The full raw-response dump in `results/` contains a stratified random sample of 201 cases; the aggregated scorecard covers all 100,000.
- **Population skew.** Although the cohort spans 127 countries, ~58% of cases originate in Europe, reflecting the engine's user base rather than a globally uniform draw. Regional composite scores are nonetheless within 0.001 of each other.

A planned V13 follow-up adds per-case multi-run variance estimation (n = 5 per case) and explicit subgroup analyses by language and laboratory reference-range provenance.

---

## Citation

If you use this benchmark or its data, please cite:

```bibtex
@techreport{klein2026kantesti_v12,
  author      = {Klein, Thomas and Bulut, Julian Emirhan},
  title       = {Clinical Validation of the Kantesti AI Engine (2.78T) on 100,000
                 Anonymised Blood Test Cases Across 127 Countries:
                 A Pre-Registered, Rubric-Based, Population-Scale Benchmark
                 (Second Update, V12)},
  institution = {Kantesti Ltd},
  address     = {London, United Kingdom},
  year        = {2026},
  month       = {April},
  type        = {Technical Report},
  number      = {V12},
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

1. Fixing the scoring rubric in source code before the first V11 engine call, and **leaving it byte-identical** for V12.
2. Publishing the full evaluation harness — including the V12 SQL case loader — under the MIT licence, so any independent researcher can re-execute the run against the same public production endpoint.
3. Publishing the aggregated 100K scorecard alongside a stratified random sample (n = 201) of full raw engine responses for inspection.

---

## Licence

The benchmark harness, scorecards, and documentation in this repository are released under the [MIT Licence](LICENSE). The Kantesti AI Engine itself is a proprietary commercial product accessed via the public production API at `app.aibloodtestinterpret.com`.

---

<p align="center">
  <em>Kantesti Ltd — Companies House No. 17090423 (England &amp; Wales)<br>
  4 Raven Road, Unit 1c3-1100, London E18 1HB, United Kingdom<br>
  <a href="https://www.kantesti.net">www.kantesti.net</a></em>
</p>
