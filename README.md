<p align="center">
  <a href="https://www.kantesti.net">
    <img src="https://www.kantesti.net/storage/2026/02/kantesti-smart-health-ai-diagnostics-identity.webp" alt="Kantesti — Smart Health AI Diagnostics" width="640">
  </a>
</p>

<h1 align="center">Kantesti AI Blood Test Benchmark — V12 November Update</h1>
<h3 align="center"><em>MedQA 94.89% · MedCalc-Bench 87.0% · MedHallu 87.6% · PubMedQA 82.4% — plus the V11 100,000-case synthetic blood-test benchmark</em></h3>

<p align="center">
  <a href="https://www.kantesti.net/kantesti-ai-blood-test-benchmark/#v12-november-update"><img src="https://img.shields.io/badge/V12-November%20Update-purple" alt="Kantesti AI V12 November Update"></a>
  <a href="#v12-november-update-15-nov-2026"><img src="https://img.shields.io/badge/MedQA%20(USMLE)-94.89%25-brightgreen" alt="MedQA USMLE accuracy 94.89%"></a>
  <a href="https://doi.org/10.6084/m9.figshare.32095435"><img src="https://img.shields.io/badge/DOI-10.6084%2Fm9.figshare.32095435-blue" alt="DOI"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/V11%20composite-99.80%25-brightgreen" alt="V11 Composite Score"></a>
  <a href="#headline-result"><img src="https://img.shields.io/badge/cohort-100%2C000%20synthetic-success" alt="Synthetic Cohort"></a>
</p>

---

## V12 November Update (15 Nov 2026)

**Kantesti AI v12 November Update** was run on **four public medical AI benchmarks** — MedQA (USMLE), MedCalc-Bench, MedHallu and PubMedQA — on 15 November 2026. Every answer is published in [`v12-november-update/benchmark.zip`](v12-november-update/benchmark.zip) so anyone can check the scores line by line.

📄 **Full write-up:** [Kantesti AI Blood Test Benchmark — V12 November Update](https://www.kantesti.net/kantesti-ai-blood-test-benchmark/#v12-november-update)

| Benchmark | Questions | Answered | Correct | Accuracy |
|---|---:|---:|---:|---:|
| **MedQA** (USMLE, 4 options, test set) | 1,273 | 1,273 | 1,208 | **94.89%** |
| **MedHallu** (pqa_labeled, hallucination detection) | 1,000 | 1,000 | 876 | **87.6%** |
| **MedCalc-Bench** (test set) | 1,100 | 1,100 | 957 | **87.0%** |
| **PubMedQA** (expert-labelled test set) | 500 | 500 | 412 | **82.4%** |
| **Total** | **3,873** | **3,873** | **3,453** | — |

**Breakdowns**

- **MedCalc-Bench by answer kind:** decimal 95.78% (n=640) · integer 76.5% (n=400) · date 63.33% (n=60)
- **MedHallu by difficulty:** easy 89.78% (n=274) · medium 88.36% (n=318) · hard 85.54% (n=408)

**Method.** Each question was asked once, with the benchmark's own answer options and context, and scored against the benchmark's answer key. Accuracy = correct ÷ answered; no question was left unanswered. These results were run and scored by Kantesti and have not been independently verified or peer-reviewed. They are exam-style accuracies, **not** diagnostic accuracy.

### Raw results: `benchmark.zip`

| File | Content |
|---|---|
| [`benchmark.zip`](v12-november-update/benchmark.zip) | Full archive (35 KB), identical to the [kantesti.net download](https://www.kantesti.net/kantesti-ai-blood-test-benchmark/#v12-november-update) |
| [`summary.md`](v12-november-update/summary.md) / [`summary.json`](v12-november-update/summary.json) | Totals and breakdowns |
| [`medqa.json`](v12-november-update/medqa.json), [`medcalc.json`](v12-november-update/medcalc.json), [`medhallu.json`](v12-november-update/medhallu.json), [`pubmedqa.json`](v12-november-update/pubmedqa.json) | One JSON line per question: gold answer, model answer, `correct` |
| [`benchmark.log`](v12-november-update/benchmark.log) | Timestamped run log |

SHA-256 of `benchmark.zip`:

```
e016c0aa9a02a5b7948ea05fa3cedba3dffb069bfaa6dbac98d473e9b7afad90
```

Verify it yourself:

```bash
cd v12-november-update && sha256sum -c benchmark.zip.sha256
```

```bash
grep -c '"correct": true' v12-november-update/medqa.json   # 1208 of 1273 lines
```

---

## V11 — Second Update: 100,000-case synthetic blood-test benchmark

A **pre-registered, rubric-based automated technical benchmark** of the [Kantesti blood-test interpretation engine](https://www.kantesti.net) on **100,000 synthetically generated test cases**, tagged with **127 country labels** and **75+ language labels** to exercise multilingual output formatting. This is the **Second Update** of the V11 Kantesti Blood Test Benchmark suite, extending the original V11 proof-of-concept (15 hand-constructed cases) to a larger synthetic cohort.

> **What this is, and what it is not.** This is an automated technical benchmark. It measures how closely the engine's **output** matches an expected report structure and term list, on **synthetic** inputs. It is **not** a clinical validation, **not** a measure of diagnostic accuracy, was **not** run on real patients, and has **not** been independently or peer-reviewed. All test cases are synthetic — **no real patient data and no personal data of any kind are used**.

> The harness in this repository is released under the MIT licence. The Kantesti engine itself is a commercial product accessed through its public production API.

---

## Update history

| Release | Date | Cohort | Content areas | Locale labels | Composite |
|---|---|---:|---:|---:|---:|
| V11 (initial) | 23 Apr 2026 | 15 synthetic cases | 7 + 1 trap bucket | — | 0.9912 |
| **V11 — Second Update** | **26 Apr 2026** | **100,000 synthetic cases** | **8** | **127** | **0.9980** |
| **V12 — November Update** | **15 Nov 2026** | **3,873 public benchmark questions** | MedQA · MedCalc-Bench · MedHallu · PubMedQA | — | see [V12](#v12-november-update-15-nov-2026) |

The V11 release exercised the rubric on hand-constructed differential-diagnosis pitfalls and over-diagnosis traps. The Second Update keeps the rubric **byte-identical** and extends the evaluation to a larger synthetic cohort.

---

## Headline result

On the same rubric, frozen in source code before the V11 run, the engine produced on the 100K synthetic cohort:

| Metric | V11 initial (n=15) | **V11 Second Update (n=100,000)** |
|---|---:|---:|
| **Composite score** | 0.9912 (99.12%) | **0.9980 (99.80%)** |
| Structural score (mean) | 0.998 | **1.000** |
| Clinical-keyword score (mean) | 0.998 | **0.996** |
| Avg. latency | 20.17 s | **13.26 s** |
| Min / max latency | 17.0 / 37.0 s | **9.0 / 16.94 s** |
| Cases scored | 15 / 15 | **100,000 / 100,000** |
| Trap-subset hyperdiagnosis | 0 / 13 flags | **0 / 87,412 flags** |

These figures describe **output conformance on generated inputs**, not diagnostic accuracy. A 201-case sample of full raw engine responses is published under [`results/`](results/) for inspection.

---

## Methodology summary

The composite score for each case is:

```
C = 0.35 × Structural + 0.55 × Clinical-keyword + 0.10 × Latency
```

- **Structural (35%)** — fraction of 7 mandatory report sections and 16 mandatory subsections present in the output.
- **Clinical-keyword (55%)** — keyword recall (70%), scoring-system recall (20%), probability-sum validity in [90, 110] (10%). Trap-subset cases carry a hyperdiagnosis penalty of up to 0.30. **This component only checks whether expected terms appear in the output; it does not assess diagnostic correctness and is not a measure of diagnostic accuracy.**
- **Latency (10%)** — 0.10 if response under 20 s, 0.05 if under 40 s, otherwise 0.

The rubric is implemented in [`benchmark_bloodtest.py`](benchmark_bloodtest.py) and was committed before the first V11 engine call. **It was not modified for the Second Update** — only the cohort size and breadth changed. See the [technical report PDF](Kantesti_AI_Engine_2_78T_Blood_Test_Benchmark_V11_Second_Update_Technical_Report.pdf) for the full methodology and discussion.

---

## Cohort coverage

### Content-area distribution (Second Update, n = 100,000 synthetic cases)

| Content area | Cases | Share |
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

Content-area labels indicate which panel templates and expected-term sets were used to generate each synthetic case; they do not represent real patients in those specialties.

### Locale labels

Each synthetic case carries one of 127 country labels and one of 75+ language labels, used to exercise locale handling. Per-label composites clustered within ~0.9971–0.9985. **This is a formatting-consistency observation on generated data — not real-world geographic coverage, not a real user base, and not clinical equivalence across populations.**

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

You need a Kantesti API credential pair, read at runtime (nothing is hard-coded):

```bash
export KANTESTI_USERNAME="your_api_username"
export KANTESTI_PASSWORD="your_api_password"
```

### 4. Run the benchmark

```bash
# Second Update default: 100,000 synthetic cases
python benchmark_bloodtest.py

# Smaller sample (e.g. n = 1,000) for quick iteration
python benchmark_bloodtest.py --limit 1000

# Localise the response language
python benchmark_bloodtest.py --lang tr

# Sandbox mode (no credit consumption)
python benchmark_bloodtest.py --sandbox
```

Each run emits four artefacts:

- `kantesti_benchmark_<timestamp>.json` — aggregated scorecard (suite + per-area + per-label)
- `kantesti_benchmark_<timestamp>_full.json` — full dump (sampled raw responses)
- `kantesti_benchmark_<timestamp>.md` — human-readable Markdown report
- `kantesti_benchmark_<timestamp>.csv` — per-case CSV for downstream analysis

The reference Second Update run from 26 April 2026 is preserved under [`results/`](results/).

> **Note on the case set.** The 100,000 cases are synthetically generated. The repository ships the generator/case set used for the run; describe its exact construction in the technical report so it matches this code. There is **no clinical database, no consent flag, and no real patient data** involved anywhere in the pipeline.

---

## Data and ethics

**All test cases in this benchmark are synthetically generated.** They are constructed laboratory panels, not records of real people. Accordingly:

- There is **no real patient data**, **no consent process**, and **no de-identification of real identifiers** involved — there is nothing to de-identify, because no personal data exists in the cohort.
- No personal data of any kind appears in this repository, in the released datasets, or in the technical report.
- Country and language values in the released artefacts are **synthetic labels** attached to generated cases; they are not linked to any real individual.

This benchmark therefore raises no data-protection obligations of its own, because it processes no personal data.

---

## Limitations

- **Synthetic data.** All cases are generated; they do not represent real patients, and results do not transfer to real-world clinical performance.
- **Conformance, not correctness.** The clinical-keyword component checks for the presence of expected terms, not diagnostic correctness.
- **Single engine, single-shot.** One engine is characterised, with one run per case. A multi-run protocol with per-case variance is planned for a later release.
- **Vendor-run.** The cohort, rubric, and scorer are all produced by the engine's vendor; the published, re-runnable harness is the mitigation, not a substitute for independent evaluation.

---

## Citation

```bibtex
@techreport{kantesti2026_v11_second_update,
  author      = {Klein, Thomas and Bulut, Julian Emirhan},
  title       = {A Pre-Registered, Rubric-Based Automated Technical Benchmark of the
                 Kantesti Blood-Test Interpretation Engine on 100,000 Synthetic Test Cases
                 --- V11 Second Update},
  institution = {Kantesti Ltd},
  address     = {London, United Kingdom},
  year        = {2026},
  month       = {April},
  type        = {Technical Report},
  number      = {V11 (Second Update)},
  doi         = {10.6084/m9.figshare.32095435},
  url         = {https://doi.org/10.6084/m9.figshare.32095435}
}
```

---

## Related links

- **V12 November Update (results page):** <https://www.kantesti.net/kantesti-ai-blood-test-benchmark/#v12-november-update>
- **Figshare (DOI):** <https://doi.org/10.6084/m9.figshare.32095435>
- **Kantesti website:** <https://www.kantesti.net>
- **Kantesti API documentation:** <https://www.kantesti.net/docs/en/endpoints/>

---

## Authors

**Thomas Klein** — Kantesti AI. ORCID: [0009-0009-1490-1321](https://orcid.org/0009-0009-1490-1321). Email: thomas.klein@kantesti.net.

**Julian Emirhan Bulut** — CEO, Kantesti Ltd. Email: julian@kantesti.net.

---

## Conflict of interest

Both authors are employed by and hold equity in Kantesti Ltd. The engine under evaluation is a commercial product of the same organisation. We disclose this openly and mitigate the obvious bias by:

1. Fixing the scoring rubric in source code before the first V11 engine call, and **leaving it byte-identical** for the Second Update.
2. Publishing the full evaluation harness under the MIT licence, so any independent researcher can re-execute the run against the same public production endpoint.
3. Publishing the aggregated 100K scorecard alongside a stratified random sample (n = 201) of full raw engine responses for inspection.

---

## Licence

The benchmark harness, scorecards, and documentation in this repository are released under the [MIT Licence](LICENSE). The Kantesti engine itself is a proprietary commercial product accessed via the public production API.

---

<p align="center">
  <em>Kantesti Ltd — Companies House No. 17090423 (England &amp; Wales)<br>
  4 Raven Road, Unit 1c3-1100, London E18 1HB, United Kingdom<br>
  <a href="https://www.kantesti.net">www.kantesti.net</a></em>
</p>
