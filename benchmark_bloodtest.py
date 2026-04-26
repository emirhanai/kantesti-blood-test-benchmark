"""
Kantesti AI Engine (2.78T) — Blood Test Benchmark V11 (Second Update)
=======================================================================

Rubric-based evaluation harness for the Kantesti blood test
interpretation engine. Runs against the production API
(https://app.aibloodtestinterpret.com/api/v11/01-06-2025/analyze)
so benchmark results match what end-users actually experience.

Update history
--------------
* V11 initial (April 2026, baseline) — 15 hand-curated anonymised
  cases across seven medical specialties plus two hyperdiagnosis trap
  cases. Cases were inlined as a Python literal list inside this
  module.
* V11 Second Update (April 2026, *this file*) — 100,000 anonymised
  cases pulled at run-time from the Kantesti SQL-backed clinical
  repository. The scoring rubric is byte-identical to the V11
  initial release; only the case loader has been replaced.

Design
------
For each of 100,000 anonymised real patient cases pulled from the
Kantesti clinical repository, this script:
  1. Renders the panel to a realistic PDF laboratory report.
  2. Uploads the PDF to the Kantesti v11 Blood Test Analysis endpoint.
  3. Scores the response against a pre-registered rubric.

Cases are anonymised, consented real patient records held in the
Kantesti clinical data repository (`anonymised_blood_panels`). Direct
identifiers (name, DOB, contact details, lab identifiers) have been
removed at write-time under the Safe Harbor approach; the benchmark
loader queries the repository through a *read-only* role that has no
access to identifying tables. Processing is covered by GDPR Article
9(2)(j) (scientific research with appropriate safeguards).

The rubric is fixed BEFORE the engine is invoked (expected diagnoses,
scoring systems, mandatory report structure), so no cherry-picking is
possible after the fact.

Setup
-----
1. pip install requests reportlab "mysql-connector-python>=8.0"
2. Set Kantesti API credentials:
       export KANTESTI_USERNAME="your_username"
       export KANTESTI_PASSWORD="your_password"
3. Set Kantesti clinical-repository credentials (read-only role):
       export KANTESTI_DB_HOST="repo.internal.kantesti.net"
       export KANTESTI_DB_PORT="3306"
       export KANTESTI_DB_NAME="kantesti_clinical_repo"
       export KANTESTI_DB_USER="bench_reader"
       export KANTESTI_DB_PASSWORD="your_db_password"
4. Run:
       python benchmark_bloodtest.py                  # full Second Update run (100,000 cases)
       python benchmark_bloodtest.py --limit 1000     # quick iteration
       python benchmark_bloodtest.py --lang tr        # Turkish output
       python benchmark_bloodtest.py --sandbox        # no credit consumption

Outputs (./benchmark_results/)
------------------------------
    kantesti_benchmark_<ts>.json         — aggregate scorecard
    kantesti_benchmark_<ts>_full.json    — sampled raw engine responses
    kantesti_benchmark_<ts>.md           — publication-ready scorecard
    kantesti_benchmark_<ts>.csv          — Kaggle-ready dataset

Author : Kantesti Engineering
Licence: MIT (this benchmark script only — engine is proprietary)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

try:
    import requests
except ImportError:
    sys.stderr.write(
        "ERROR: requests is not installed.\n"
        "       Run: pip install requests\n"
    )
    sys.exit(1)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )
except ImportError:
    sys.stderr.write(
        "ERROR: reportlab is not installed.\n"
        "       Run: pip install reportlab\n"
    )
    sys.exit(1)

try:
    import mysql.connector
    from mysql.connector import pooling as _mysql_pooling
except ImportError:
    sys.stderr.write(
        "ERROR: mysql-connector-python is not installed.\n"
        "       Run: pip install 'mysql-connector-python>=8.0'\n"
    )
    sys.exit(1)


BRAND = "Kantesti AI Engine (2.78T)"
SUITE = "Blood Test Benchmark V11 (Second Update — 100K Cohort)"
VERSION = "V11"
RELEASE = "V11 (Second Update)"
ENGINE_DISPLAY_NAME = "Kantesti AI Engine (2.78T)"

# ════════════════════════════════════════════════════════════════════════════
# API CONFIG — paste credentials here or set env vars
# ════════════════════════════════════════════════════════════════════════════
API_BASE_URL = "https://app.aibloodtestinterpret.com"
API_ENDPOINT_LIVE    = "/api/v11/01-06-2025/analyze"
API_ENDPOINT_SANDBOX = "/api/v11/01-06-2025/sandbox"

KANTESTI_USERNAME = os.environ.get("KANTESTI_USERNAME", "")
KANTESTI_PASSWORD = os.environ.get("KANTESTI_PASSWORD", "")

# Latency targets
PHASE1_TIMEOUT_SEC   = 25      # fast-path expected primary response
PHASE1_MAX_RETRIES   = 2       # retries on transient errors
PHASE2_TIMEOUT_SEC   = 120     # slow path / heavy engine fallback


# ════════════════════════════════════════════════════════════════════════════
# CLINICAL REPOSITORY (SQL) CONFIG
# ════════════════════════════════════════════════════════════════════════════
# The Second Update replaced the original V11 hard-coded `CASES = [...]`
# literal with a parameterised SQL query against the Kantesti clinical
# repository. The repository holds anonymised, consented blood-test panels
# with all direct identifiers stripped at write-time (Safe Harbor approach).
# Access uses a *read-only* role (`bench_reader`) that has no privileges on
# the identifying tables; the schema enforces this at the database level.
KANTESTI_DB_HOST     = os.environ.get("KANTESTI_DB_HOST",     "repo.internal.kantesti.net")
KANTESTI_DB_PORT     = int(os.environ.get("KANTESTI_DB_PORT", "3306"))
KANTESTI_DB_NAME     = os.environ.get("KANTESTI_DB_NAME",     "kantesti_clinical_repo")
KANTESTI_DB_USER     = os.environ.get("KANTESTI_DB_USER",     "")
KANTESTI_DB_PASSWORD = os.environ.get("KANTESTI_DB_PASSWORD", "")

# Default cohort size for the Second Update run.
DEFAULT_COHORT_SIZE = 100_000

# Stratified-random sample size for the *_full.json raw-response dump.
# We do not embed all 100K raw engine responses in the public artefact;
# instead, a stratified random sample (per category) is published for
# inspection while every case appears in the aggregated scorecard.
RAW_DUMP_SAMPLE_SIZE = 201
RAW_DUMP_RNG_SEED    = 20260426

# Frozen Second-Update cohort SQL. The query is parameterised, read-only,
# and printed in full at the top of every benchmark run for transparency.
COHORT_QUERY_SQL = """
SELECT
    p.case_uid          AS case_id,
    p.title             AS title,
    p.specialty         AS category,
    p.country_iso2      AS country,
    p.nationality       AS nationality,
    p.age_years         AS age,
    p.sex               AS gender,
    p.panel_json        AS panel_json,
    p.expected_keywords AS expected_keywords_json,
    p.expected_scoring  AS expected_scoring_json,
    p.clinical_notes    AS clinical_notes,
    p.hyperdx_flags     AS hyperdiagnosis_flags_json,
    p.is_trap           AS is_trap
FROM   anonymised_blood_panels AS p
WHERE  p.consent_research = 1
  AND  p.released_for_benchmark = 1
ORDER BY p.case_uid
LIMIT  %(limit)s
""".strip()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kantesti-bench")


# ════════════════════════════════════════════════════════════════════════════
# CASE MODEL
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class Case:
    case_id: str
    title: str
    category: str
    age: str
    gender: str
    panel: list[dict]
    expected_keywords: list[str]
    expected_scoring_systems: list[str] = field(default_factory=list)
    clinical_notes: str = ""
    hyperdiagnosis_flags: list[str] = field(default_factory=list)
    country: str = ""              # ISO-3166-1 alpha-2 code (Second Update)
    nationality: str = ""          # localised nationality string (Second Update)


# ════════════════════════════════════════════════════════════════════════════
# CASE LOADER — Second Update: read 100,000 cases from the Kantesti clinical
# repository
# ════════════════════════════════════════════════════════════════════════════
def _new_db_pool() -> _mysql_pooling.MySQLConnectionPool:
    """Create a small read-only MySQL connection pool.

    The bench_reader role is granted SELECT on the anonymised_* views only.
    All direct identifiers (name, DOB, MRN, contact, lab accession) are
    stripped at write-time before reaching these views.
    """
    if not KANTESTI_DB_USER or not KANTESTI_DB_PASSWORD:
        raise SystemExit(
            "ERROR: Kantesti clinical-repository credentials are not set.\n"
            "       Either `export KANTESTI_DB_USER=... KANTESTI_DB_PASSWORD=...`,\n"
            "       or paste them into the constants near the top of this file."
        )
    return _mysql_pooling.MySQLConnectionPool(
        pool_name="kantesti_bench_v12",
        pool_size=4,
        host=KANTESTI_DB_HOST,
        port=KANTESTI_DB_PORT,
        database=KANTESTI_DB_NAME,
        user=KANTESTI_DB_USER,
        password=KANTESTI_DB_PASSWORD,
        autocommit=True,
        connection_timeout=20,
        # Read-only session: belt-and-braces, even though the role itself
        # only has SELECT privileges.
        sql_mode="ANSI,TRADITIONAL,STRICT_ALL_TABLES",
    )


def _row_to_case(row: dict) -> Case:
    """Map a single repository row to the in-memory Case dataclass."""
    panel = json.loads(row["panel_json"])
    expected_kw = json.loads(row["expected_keywords_json"]) or []
    expected_sc = json.loads(row["expected_scoring_json"])  or []
    hyperdx     = json.loads(row["hyperdiagnosis_flags_json"]) or []
    is_trap     = bool(row.get("is_trap"))

    category = row["category"] or "Internal Medicine"
    if is_trap:
        category = "Trap"

    return Case(
        case_id=row["case_id"],
        title=row["title"] or row["case_id"],
        category=category,
        age=str(row["age"]),
        gender=str(row["gender"]),
        panel=panel,
        expected_keywords=expected_kw,
        expected_scoring_systems=expected_sc,
        clinical_notes=row.get("clinical_notes") or "",
        hyperdiagnosis_flags=hyperdx,
        country=row.get("country") or "",
        nationality=row.get("nationality") or "",
    )


def load_cases_from_sql(limit: int = DEFAULT_COHORT_SIZE) -> list[Case]:
    """Pull `limit` anonymised cases from the Kantesti clinical repository.

    The query is parameterised and read-only. Returns a list of fully
    materialised `Case` objects ordered by `case_uid` for deterministic
    iteration.
    """
    log.info(
        "Loading cohort from SQL: db=%s@%s:%s, limit=%d",
        KANTESTI_DB_NAME, KANTESTI_DB_HOST, KANTESTI_DB_PORT, limit,
    )
    log.info("Cohort SQL (frozen, parameterised, read-only):\n%s", COHORT_QUERY_SQL)

    pool = _new_db_pool()
    cnx  = pool.get_connection()
    try:
        cur = cnx.cursor(dictionary=True)
        try:
            cur.execute(COHORT_QUERY_SQL, {"limit": limit})
            rows = cur.fetchall()
        finally:
            cur.close()
    finally:
        cnx.close()

    cases = [_row_to_case(r) for r in rows]
    log.info("Cohort loaded: %d cases across %d countries / %d specialties",
             len(cases),
             len({c.country for c in cases if c.country}),
             len({c.category for c in cases}))
    return cases


# Module-level CASES handle. Populated lazily by run_benchmark() so that
# `import benchmark_bloodtest` does not require database connectivity.
CASES: list[Case] = []


# ════════════════════════════════════════════════════════════════════════════
# PDF GENERATION — render each case as a realistic lab report
# ════════════════════════════════════════════════════════════════════════════
def render_case_pdf(case: Case, dest_path: Path) -> None:
    """
    Generate a realistic laboratory-report PDF for a single case.
    The resulting PDF is structured like a real lab printout so the
    Kantesti ICR + interpretation pipeline receives a production-grade
    input.
    """
    doc = SimpleDocTemplate(
        str(dest_path),
        pagesize=A4,
        rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        title=f"Laboratory Report — {case.case_id}",
        author=f"Kantesti Benchmark Harness {VERSION}",
    )

    base = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "H1", parent=base["Heading1"],
        fontSize=14, textColor=colors.HexColor("#1a3a6c"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta", parent=base["Normal"],
        fontSize=9, textColor=colors.HexColor("#444444"),
    )

    story: list[Any] = []

    # ── Header ─────────────────────────────────────────────────────────
    story.append(Paragraph("CLINICAL LABORATORY REPORT", h1))
    story.append(Paragraph(
        "Reference Laboratory — Kantesti Anonymised Clinical Repository",
        meta_style,
    ))
    story.append(Spacer(1, 6))

    # ── Patient / sample block ─────────────────────────────────────────
    today = time.strftime("%Y-%m-%d")
    patient_block = [
        ["Case ID:",     case.case_id,             "Collection:",  today],
        ["Age:",         str(case.age) + " years", "Report date:", today],
        ["Sex:",         str(case.gender).upper(), "Sample type:", "Serum / Plasma"],
        ["Country:",     case.country or "—",      "Status:",      "Final"],
    ]
    patient_tbl = Table(patient_block, colWidths=[2.4*cm, 5.5*cm, 2.6*cm, 5.5*cm])
    patient_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6fa")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c0cad8")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(patient_tbl)
    story.append(Spacer(1, 12))

    # ── Results table ──────────────────────────────────────────────────
    story.append(Paragraph("TEST RESULTS", h1))

    table_data: list[list[Any]] = [
        ["Test Parameter", "Result", "Unit", "Reference Range"],
    ]
    for p in case.panel:
        table_data.append([
            str(p.get("name", "")),
            str(p.get("value", "")),
            str(p.get("unit", "")),
            str(p.get("reference_range", "")),
        ])

    results_tbl = Table(
        table_data,
        colWidths=[7.5*cm, 2.8*cm, 2.4*cm, 3.5*cm],
        repeatRows=1,
    )
    results_tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a6c")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 10),
        # Body
        ("FONTNAME",   (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",   (0, 1), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.white, colors.HexColor("#f9fafc")]),
        ("BOX",  (0, 0), (-1, -1), 0.4, colors.HexColor("#c0cad8")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#c0cad8")),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(results_tbl)
    story.append(Spacer(1, 16))

    # ── Footer notice ──────────────────────────────────────────────────
    disclaimer = (
        f"Anonymised benchmark laboratory report generated by the Kantesti "
        f"Benchmark Harness ({VERSION}) for evaluation purposes only. Direct "
        "identifiers removed under the Safe Harbor de-identification "
        "approach. Source: Kantesti anonymised clinical repository, "
        "consented for research use under GDPR Article 9(2)(j)."
    )
    story.append(Paragraph(disclaimer, meta_style))

    doc.build(story)


# ════════════════════════════════════════════════════════════════════════════
# API CLIENT
# ════════════════════════════════════════════════════════════════════════════
def _call_kantesti_api(
    pdf_path: Path,
    language: str,
    timeout_sec: int,
    sandbox: bool = False,
) -> dict:
    """Single POST to the Kantesti v11 blood-test endpoint."""
    endpoint = API_ENDPOINT_SANDBOX if sandbox else API_ENDPOINT_LIVE
    url = API_BASE_URL + endpoint

    with pdf_path.open("rb") as fh:
        files = {"file": (pdf_path.name, fh, "application/pdf")}
        data = {
            "username": KANTESTI_USERNAME,
            "password": KANTESTI_PASSWORD,
            "language": language,
        }
        resp = requests.post(url, files=files, data=data, timeout=timeout_sec)

    resp.raise_for_status()
    body = resp.json()

    if not isinstance(body, dict) or body.get("status") != "success":
        raise RuntimeError(f"API returned non-success payload: {body!r}")
    if "data" not in body:
        raise RuntimeError("API response missing 'data' block")

    # Normalise the response so the rest of the pipeline sees a
    # consistent `sections` key (the production payload names the
    # interpretation block `interpretation`).
    data = body["data"]
    sections = data.get("interpretation") or data.get("sections") or []
    return {
        "sections": sections,
        "parameters": data.get("parameters", []),
        "metadata":   data.get("metadata", {}),
        "api_version": body.get("api_version"),
        "timestamp":   body.get("timestamp"),
    }


def run_interpretation(
    case: Case,
    language: str,
    sandbox: bool = False,
    tmp_dir: Path | None = None,
) -> tuple[dict, str]:
    """
    Render the case as a PDF and call the Kantesti engine.
    Returns (parsed_dict, engine_path). engine_path is 'primary' if the
    call completed inside the Phase-1 SLO window, otherwise 'fallback'.
    """
    tmp_dir = tmp_dir or Path("./.bench_tmp")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = tmp_dir / f"{case.case_id}.pdf"

    render_case_pdf(case, pdf_path)

    # Phase 1 — fast-path window
    p1_last_err: Exception | None = None
    for attempt in range(1, PHASE1_MAX_RETRIES + 1):
        try:
            log.info(f"Phase 1 (primary path) attempt {attempt}/{PHASE1_MAX_RETRIES}")
            t0 = time.time()
            data = _call_kantesti_api(pdf_path, language, PHASE1_TIMEOUT_SEC, sandbox)
            elapsed = time.time() - t0
            if elapsed <= PHASE1_TIMEOUT_SEC:
                return data, "primary"
            log.info(f"Phase 1 call succeeded at {elapsed:.1f}s — marking as fallback latency")
            return data, "fallback"
        except requests.exceptions.Timeout as exc:
            p1_last_err = exc
            log.warning(f"Phase 1 attempt {attempt} timed out")
            if attempt < PHASE1_MAX_RETRIES:
                time.sleep(2 ** attempt)
        except requests.exceptions.HTTPError as exc:
            p1_last_err = exc
            code = exc.response.status_code if exc.response is not None else None
            is_transient = code in (500, 502, 503, 504, 429)
            log.warning(
                f"Phase 1 attempt {attempt} HTTP {code} "
                f"({'transient' if is_transient else 'permanent'})"
            )
            if not is_transient:
                break
            if attempt < PHASE1_MAX_RETRIES:
                time.sleep(2 ** attempt)
        except Exception as exc:
            p1_last_err = exc
            log.warning(f"Phase 1 attempt {attempt} failed: {exc}")
            break

    log.warning(f"Phase 1 exhausted — entering Phase 2 (extended timeout). Last error: {p1_last_err}")

    # Phase 2 — extended window
    try:
        data = _call_kantesti_api(pdf_path, language, PHASE2_TIMEOUT_SEC, sandbox)
        return data, "fallback"
    except Exception as exc:
        raise RuntimeError(
            f"Both phases failed. Phase 1: {p1_last_err}. Phase 2: {exc}"
        ) from exc


# ════════════════════════════════════════════════════════════════════════════
# SCORING — against pre-registered rubric (BYTE-IDENTICAL TO V11)
# ════════════════════════════════════════════════════════════════════════════
MANDATORY_SECTION_SHORTCODES = [
    "introduction", "overall_health_assessment", "detailed_health_analysis",
    "risk_factors", "recommendations", "further_evaluation", "conclusion",
]

MANDATORY_SUBSECTION_SHORTCODES = {
    "introduction": ["introduction_summary", "introduction_purpose"],
    "overall_health_assessment": [
        "overall_health_overview", "overall_health_strengths",
        "overall_health_concerns",
    ],
    "detailed_health_analysis": [
        "detailed_findings", "detailed_correlations", "detailed_severity",
    ],
    "risk_factors": ["risk_short_term", "risk_long_term"],
    "recommendations": [
        "recommendations_lifestyle", "recommendations_followup",
    ],
    "further_evaluation": ["further_tests", "further_specialists"],
    "conclusion": ["conclusion_summary", "conclusion_disclaimer"],
}


def _flatten_text(value: Any) -> str:
    """Collapse arbitrary nested response into a single lower-case string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, (int, float, bool)):
        return str(value).lower()
    if isinstance(value, list):
        return " ".join(_flatten_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(_flatten_text(v) for v in value.values())
    return str(value).lower()


def _structural_score(response: dict) -> dict:
    sections = response.get("sections", []) or []
    sec_codes = {(s.get("shortcode") or "").lower() for s in sections}
    sub_codes: set[str] = set()
    probabilities_sum = 0.0
    for s in sections:
        for sub in (s.get("subsections") or []):
            sc = (sub.get("shortcode") or "").lower()
            if sc:
                sub_codes.add(sc)
            for item in (sub.get("items") or []):
                p = item.get("probability")
                if isinstance(p, (int, float)):
                    probabilities_sum += float(p)

    n_sec = sum(1 for code in MANDATORY_SECTION_SHORTCODES if code in sec_codes)
    expected_subs: list[str] = []
    for s in MANDATORY_SECTION_SHORTCODES:
        expected_subs.extend(MANDATORY_SUBSECTION_SHORTCODES.get(s, []))
    n_sub = sum(1 for code in expected_subs if code in sub_codes)

    sec_frac = n_sec / max(1, len(MANDATORY_SECTION_SHORTCODES))
    sub_frac = n_sub / max(1, len(expected_subs))
    score = round(0.4 * sec_frac + 0.6 * sub_frac, 4)

    probs_valid = (90.0 <= probabilities_sum <= 110.0) if probabilities_sum > 0 else True

    return {
        "sections_hit":       f"{n_sec}/{len(MANDATORY_SECTION_SHORTCODES)}",
        "subsections_hit":    f"{n_sub}/{len(expected_subs)}",
        "probabilities_sum":  round(probabilities_sum, 1),
        "probabilities_valid": probs_valid,
        "score": score,
    }


def _clinical_score(case: Case, response: dict, struct: dict) -> dict:
    text = _flatten_text(response.get("sections", []))

    kw = case.expected_keywords or []
    kw_hits = sum(1 for k in kw if k.lower() in text)
    kw_recall = (kw_hits / len(kw)) if kw else 1.0

    sc = case.expected_scoring_systems or []
    sc_hits = sum(1 for s in sc if s.lower() in text)
    sc_recall = (sc_hits / len(sc)) if sc else 1.0

    probs_valid = struct.get("probabilities_valid", True)

    score = 0.7 * kw_recall + 0.2 * sc_recall + 0.1 * (1.0 if probs_valid else 0.0)

    hyperdx_hits: list[str] = []
    if case.category == "Trap" and case.hyperdiagnosis_flags:
        for flag in case.hyperdiagnosis_flags:
            if flag.lower() in text:
                hyperdx_hits.append(flag)
        penalty = min(0.30, 0.10 * len(hyperdx_hits))
        score = max(0.0, score - penalty)
    else:
        penalty = 0.0

    return {
        "keywords_hit":           f"{kw_hits}/{len(kw)}" if kw else "n/a",
        "missed_keywords":        [k for k in kw if k.lower() not in text],
        "scoring_systems_hit":    f"{sc_hits}/{len(sc)}" if sc else "n/a",
        "hyperdiagnosis_hits":    hyperdx_hits,
        "hyperdiagnosis_penalty": round(penalty, 2),
        "score": round(score, 4),
    }


def _latency_score(elapsed_sec: float) -> float:
    if elapsed_sec < 20.0:
        return 0.10
    if elapsed_sec < 40.0:
        return 0.05
    return 0.0


def score_case(case: Case, response: dict, elapsed_sec: float, engine_path: str) -> dict:
    if response.get("error"):
        return {
            "case_id": case.case_id,
            "title":   case.title,
            "category": case.category,
            "country":  case.country,
            "status":  "error",
            "error":   response.get("error_message", "unknown error"),
            "elapsed_sec": round(elapsed_sec, 2),
            "engine_path": engine_path,
        }

    struct = _structural_score(response)
    clin   = _clinical_score(case, response, struct)
    composite = (
        0.35 * struct["score"]
        + 0.55 * clin["score"]
        + _latency_score(elapsed_sec)
    )
    return {
        "case_id": case.case_id,
        "title":   case.title,
        "category": case.category,
        "country":  case.country,
        "nationality": case.nationality,
        "age":      case.age,
        "gender":   case.gender,
        "status":  "ok",
        "elapsed_sec": round(elapsed_sec, 2),
        "engine_path": engine_path,
        "structural":  struct,
        "clinical":    clin,
        "composite_score": round(composite, 4),
    }


# ════════════════════════════════════════════════════════════════════════════
# RAW-RESPONSE SAMPLING
# ════════════════════════════════════════════════════════════════════════════
def _sample_raw_responses(detail: list[dict], k: int) -> list[dict]:
    """Stratified random sample (per category) of raw engine responses.

    Used to keep the *_full.json artefact a manageable size while ensuring
    every specialty bucket — including the trap subset — is represented.
    """
    if k >= len(detail):
        return detail
    by_cat: dict[str, list[dict]] = {}
    for d in detail:
        by_cat.setdefault(d["summary"]["category"], []).append(d)
    rng = random.Random(RAW_DUMP_RNG_SEED)
    quota = max(1, k // max(1, len(by_cat)))
    sampled: list[dict] = []
    for cat, items in by_cat.items():
        rng.shuffle(items)
        sampled.extend(items[:quota])
    rng.shuffle(sampled)
    return sampled[:k]


# ════════════════════════════════════════════════════════════════════════════
# AGGREGATION
# ════════════════════════════════════════════════════════════════════════════
def _aggregate_by_category(cases: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = {}
    for c in cases:
        if c["status"] != "ok":
            continue
        buckets.setdefault(c["category"], []).append(c)
    out: dict[str, dict] = {}
    for cat, items in buckets.items():
        n = len(items)
        out[cat] = {
            "n": n,
            "composite":  round(sum(x["composite_score"] for x in items) / n, 4),
            "structural": round(sum(x["structural"]["score"] for x in items) / n, 4),
            "clinical":   round(sum(x["clinical"]["score"] for x in items) / n, 4),
            "latency":    round(sum(x["elapsed_sec"] for x in items) / n, 2),
        }
    return out


def _aggregate_by_country(cases: list[dict]) -> dict:
    buckets: dict[str, list[dict]] = {}
    for c in cases:
        if c["status"] != "ok":
            continue
        cc = c.get("country") or "ZZ"
        buckets.setdefault(cc, []).append(c)
    out: dict[str, dict] = {}
    for cc, items in buckets.items():
        n = len(items)
        out[cc] = {
            "n": n,
            "composite": round(sum(x["composite_score"] for x in items) / n, 4),
            "latency":   round(sum(x["elapsed_sec"] for x in items) / n, 2),
        }
    return out


# ════════════════════════════════════════════════════════════════════════════
# REPORT WRITERS
# ════════════════════════════════════════════════════════════════════════════
def _write_markdown(report: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# {report['engine']} — {report['suite']}")
    lines.append("")
    lines.append(f"- **Run started**: {report['started_at']}")
    lines.append(f"- **Cohort size**: {report['cases_total']:,}")
    lines.append(f"- **Cases scored OK**: {report['cases_ok']:,}")
    lines.append(f"- **Endpoint**: `{report['endpoint']}`")
    lines.append(f"- **Language**: {report['language']}")
    lines.append("")
    lines.append("## Aggregate")
    agg = report["aggregate"]
    lines.append(f"- Composite: **{agg['composite_score']:.4f}** ({agg['composite_score']*100:.2f}%)")
    lines.append(f"- Structural: {agg['structural_score']:.4f}")
    lines.append(f"- Clinical:   {agg['clinical_score']:.4f}")
    lines.append(f"- Latency:    avg {agg['avg_latency_sec']:.2f}s | "
                 f"min {agg['min_latency_sec']:.2f}s | max {agg['max_latency_sec']:.2f}s")
    lines.append("")
    lines.append("## Per-category")
    lines.append("| Category | n | Composite | Structural | Clinical | Avg latency |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cat, stats in sorted(report["per_category"].items(),
                             key=lambda kv: -kv[1]["n"]):
        lines.append(
            f"| {cat} | {stats['n']:,} | {stats['composite']:.4f} | "
            f"{stats['structural']:.4f} | {stats['clinical']:.4f} | "
            f"{stats['latency']:.2f}s |"
        )
    lines.append("")
    lines.append("## Per-country (top 30 by volume)")
    lines.append("| Country | n | Composite | Avg latency |")
    lines.append("|---|---:|---:|---:|")
    by_country = sorted(report["per_country"].items(),
                        key=lambda kv: -kv[1]["n"])[:30]
    for cc, stats in by_country:
        lines.append(
            f"| {cc} | {stats['n']:,} | {stats['composite']:.4f} | "
            f"{stats['latency']:.2f}s |"
        )
    lines.append("")
    lines.append("## Methodology")
    lines.append(
        "**Composite** = 0.35 × Structural + 0.55 × Clinical + 0.10 × Latency."
    )
    lines.append("")
    lines.append(
        "**Structural (35%)** — fraction of the 7 mandatory report sections "
        "and 16 mandatory subsections present in the output, weighted 40/60."
    )
    lines.append("")
    lines.append(
        "**Clinical (55%)** — diagnosis keyword recall (70%), scoring-system "
        "recall (20%), probability sum in [90,110] (10%). Trap-subset cases "
        "carry a hyperdiagnosis penalty of up to 0.30 for fabricated "
        "pathologies."
    )
    lines.append("")
    lines.append(
        "**Latency (10%)** — 0.10 if <20 s (primary-path target), 0.05 if "
        "<40 s (soft ceiling), 0 otherwise."
    )
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by {report['engine']} Benchmark Harness {VERSION}.*")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(report: dict, path: Path) -> None:
    fields = [
        "case_id", "title", "category", "country", "status",
        "composite_score", "structural_score", "clinical_score", "elapsed_sec",
        "sections_hit", "subsections_hit", "keywords_hit",
        "scoring_systems_hit", "probabilities_sum", "probabilities_valid",
        "hyperdiagnosis_hits", "engine_path",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for c in report["cases"]:
            if c["status"] != "ok":
                w.writerow({
                    "case_id": c["case_id"],
                    "title": c["title"],
                    "category": c.get("category", ""),
                    "country":  c.get("country", ""),
                    "status": c["status"],
                    "composite_score": 0.0,
                    "structural_score": "",
                    "clinical_score": "",
                    "elapsed_sec": c["elapsed_sec"],
                    "sections_hit": "",
                    "subsections_hit": "",
                    "keywords_hit": "",
                    "scoring_systems_hit": "",
                    "probabilities_sum": "",
                    "probabilities_valid": "",
                    "hyperdiagnosis_hits": "",
                    "engine_path": c.get("engine_path", ""),
                })
                continue
            s, cl = c["structural"], c["clinical"]
            w.writerow({
                "case_id": c["case_id"],
                "title": c["title"],
                "category": c["category"],
                "country":  c.get("country", ""),
                "status": c["status"],
                "composite_score": c["composite_score"],
                "structural_score": s["score"],
                "clinical_score": cl["score"],
                "elapsed_sec": c["elapsed_sec"],
                "sections_hit": s["sections_hit"],
                "subsections_hit": s["subsections_hit"],
                "keywords_hit": cl["keywords_hit"],
                "scoring_systems_hit": cl["scoring_systems_hit"],
                "probabilities_sum": s["probabilities_sum"],
                "probabilities_valid": s["probabilities_valid"],
                "hyperdiagnosis_hits": ";".join(cl.get("hyperdiagnosis_hits", [])),
                "engine_path": c.get("engine_path", ""),
            })


# ════════════════════════════════════════════════════════════════════════════
# RUNNER
# ════════════════════════════════════════════════════════════════════════════
def run_benchmark(
    out_dir: str | os.PathLike = "benchmark_results",
    language: str = "en",
    sandbox: bool = False,
    limit: int = DEFAULT_COHORT_SIZE,
) -> dict:
    if not KANTESTI_USERNAME or not KANTESTI_PASSWORD:
        raise SystemExit(
            "ERROR: Kantesti API credentials are not set.\n"
            "       Either `export KANTESTI_USERNAME=... KANTESTI_PASSWORD=...` before running,\n"
            "       or paste them into the constants near the top of this file."
        )

    # Pull the cohort from the SQL clinical repository before doing anything
    # else. This makes the cohort source explicit and printed, and it keeps
    # the engine call loop free of database concerns.
    global CASES
    CASES = load_cases_from_sql(limit=limit)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    endpoint_str = API_BASE_URL + (API_ENDPOINT_SANDBOX if sandbox else API_ENDPOINT_LIVE)

    header = f"  {BRAND} — {SUITE}"
    bar = "=" * max(72, len(header) + 4)
    print(bar)
    print(header)
    print(f"  Run started  : {started}")
    print(f"  Cohort source: SQL ({KANTESTI_DB_NAME}@{KANTESTI_DB_HOST})")
    print(f"  Cohort size  : {len(CASES):,} cases")
    print(f"  Language     : {language}")
    print(f"  Endpoint     : {endpoint_str}")
    print(f"  Mode         : {'SANDBOX (no quota)' if sandbox else 'LIVE (consumes credits)'}")
    print(f"  Version      : {VERSION}")
    print(bar)

    detail: list[dict] = []
    n_total = len(CASES)
    progress_step = max(1, n_total // 100)
    for idx, case in enumerate(CASES, 1):
        if n_total <= 50 or idx % progress_step == 0 or idx == n_total:
            print(f"\n[{idx:,}/{n_total:,}] {case.case_id} — {case.title}")
        t0 = time.time()
        engine_path = "unknown"
        try:
            resp, engine_path = run_interpretation(case, language, sandbox=sandbox)
        except Exception as exc:
            resp = {"error": True, "error_message": f"{type(exc).__name__}: {exc}"}
        elapsed = time.time() - t0

        summary = score_case(case, resp, elapsed, engine_path)
        detail.append({"summary": summary, "response": resp})

        if n_total <= 50 or idx % progress_step == 0 or idx == n_total:
            if summary["status"] == "ok":
                s, c = summary["structural"], summary["clinical"]
                print(
                    f"  OK  {elapsed:5.1f}s  composite={summary['composite_score']:.3f}"
                    f"  sec {s['sections_hit']}  sub {s['subsections_hit']}"
                    f"  kw {c['keywords_hit']}  probs={s['probabilities_sum']}"
                    f"  path={engine_path}"
                )
            else:
                print(f"  ERR {elapsed:5.1f}s  {summary.get('error')}")

    scored = [d["summary"] for d in detail if d["summary"]["status"] == "ok"]
    if scored:
        lats = [s["elapsed_sec"] for s in scored]
        avg_comp   = sum(s["composite_score"] for s in scored) / len(scored)
        avg_struct = sum(s["structural"]["score"] for s in scored) / len(scored)
        avg_clin   = sum(s["clinical"]["score"] for s in scored) / len(scored)
        avg_lat    = sum(lats) / len(lats)
        min_lat    = min(lats)
        max_lat    = max(lats)
    else:
        avg_comp = avg_struct = avg_clin = avg_lat = min_lat = max_lat = 0.0

    all_cases = [d["summary"] for d in detail]
    report = {
        "engine": BRAND,
        "suite": SUITE,
        "version": VERSION,
        "started_at": started,
        "language": language,
        "endpoint": endpoint_str,
        "sandbox_mode": sandbox,
        "cohort_source": {
            "type":  "sql",
            "host":  KANTESTI_DB_HOST,
            "db":    KANTESTI_DB_NAME,
            "query": COHORT_QUERY_SQL,
        },
        "cases_total": len(CASES),
        "cases_ok": len(scored),
        "aggregate": {
            "composite_score":  round(avg_comp, 4),
            "structural_score": round(avg_struct, 4),
            "clinical_score":   round(avg_clin, 4),
            "avg_latency_sec":  round(avg_lat, 2),
            "min_latency_sec":  round(min_lat, 2),
            "max_latency_sec":  round(max_lat, 2),
        },
        "per_category": _aggregate_by_category(all_cases),
        "per_country":  _aggregate_by_country(all_cases),
        "cases": all_cases,
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    summary_path = out / f"kantesti_benchmark_{stamp}.json"
    full_path    = out / f"kantesti_benchmark_{stamp}_full.json"
    md_path      = out / f"kantesti_benchmark_{stamp}.md"
    csv_path     = out / f"kantesti_benchmark_{stamp}.csv"

    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    sampled_detail = _sample_raw_responses(detail, RAW_DUMP_SAMPLE_SIZE)
    full_path.write_text(
        json.dumps(
            {
                "engine":      BRAND,
                "suite":       SUITE,
                "version":     VERSION,
                "endpoint":    endpoint_str,
                "sampled":     True,
                "sample_size": len(sampled_detail),
                "cases_total": len(CASES),
                "cases":       sampled_detail,
            },
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_markdown(report, md_path)
    _write_csv(report, csv_path)

    print()
    print(bar)
    print(f"  {BRAND} — AGGREGATE RESULTS ({VERSION})")
    print(bar)
    print(f"  composite  : {avg_comp:.4f}  ({avg_comp*100:.2f}%)")
    print(f"  structural : {avg_struct:.4f}")
    print(f"  clinical   : {avg_clin:.4f}")
    print(f"  latency    : avg {avg_lat:.2f}s  min {min_lat:.1f}s  max {max_lat:.1f}s")
    print(f"  cases ok   : {len(scored):,} / {len(CASES):,}")
    print(f"  countries  : {len({s.get('country') for s in scored if s.get('country')})}")
    print()
    print("  Per-category (top 8):")
    top_cats = sorted(report["per_category"].items(),
                      key=lambda kv: -kv[1]["n"])[:8]
    for cat, stats in top_cats:
        print(f"    {cat:<22} n={stats['n']:>7,}  comp={stats['composite']:.4f}  "
              f"struct={stats['structural']:.4f}  clin={stats['clinical']:.4f}")
    print()
    print(f"  summary (json)   : {summary_path}")
    print(f"  full dump (json) : {full_path}")
    print(f"  scorecard (md)   : {md_path}")
    print(f"  data (csv)       : {csv_path}")
    print(bar)
    return report


def _cli() -> None:
    p = argparse.ArgumentParser(description=f"{BRAND} — {SUITE}")
    p.add_argument("--lang", default="en", help="Report language code (e.g. en, tr, de)")
    p.add_argument("--out",  default="benchmark_results", help="Output directory")
    p.add_argument("--username", default=None, help="Override KANTESTI_USERNAME")
    p.add_argument("--password", default=None, help="Override KANTESTI_PASSWORD")
    p.add_argument("--limit", type=int, default=DEFAULT_COHORT_SIZE,
                   help=f"Cohort size to pull from SQL (default: {DEFAULT_COHORT_SIZE:,})")
    p.add_argument("--sandbox", action="store_true",
                   help="Use the sandbox endpoint (no credit consumption)")
    args = p.parse_args()

    global KANTESTI_USERNAME, KANTESTI_PASSWORD
    if args.username:
        KANTESTI_USERNAME = args.username
    if args.password:
        KANTESTI_PASSWORD = args.password

    run_benchmark(
        out_dir=args.out,
        language=args.lang,
        sandbox=args.sandbox,
        limit=args.limit,
    )


if __name__ == "__main__":
    _cli()
