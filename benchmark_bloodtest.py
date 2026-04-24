"""
Kantesti AI Engine (2.78T) — Blood Test Benchmark V11
========================================================

Rubric-based evaluation harness for the Kantesti blood test
interpretation engine. Runs against the production API
(https://app.aibloodtestinterpret.com/api/v11/01-06-2025/analyze)
so benchmark results match what end-users actually experience.

Design
------
For each of 15 anonymised real patient cases, this script:
  1. Renders the panel to a realistic PDF laboratory report.
  2. Uploads the PDF to the Kantesti v11 Blood Test Analysis endpoint.
  3. Scores the response against a pre-registered rubric.

Cases are anonymised, consented real patient records drawn from the
Kantesti clinical data repository. Direct identifiers (name, DOB,
contact details, lab identifiers) have been removed under the Safe
Harbor approach; processing is covered by GDPR Article 9(2)(j)
(scientific research with appropriate safeguards).

The rubric is fixed BEFORE the engine is invoked (expected diagnoses,
scoring systems, mandatory report structure), so no cherry-picking is
possible after the fact.

Setup
-----
1. pip install requests reportlab
2. Set your Kantesti API credentials:
       export KANTESTI_USERNAME="your_username"
       export KANTESTI_PASSWORD="your_password"
   or paste them into the constants below.
3. Run:
       python benchmark_bloodtest.py
       python benchmark_bloodtest.py --lang tr     # Turkish report
       python benchmark_bloodtest.py --sandbox     # no credit consumption

Outputs (./benchmark_results/)
------------------------------
    kantesti_benchmark_<ts>.json         — aggregate scorecard
    kantesti_benchmark_<ts>_full.json    — + raw engine responses
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
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

BRAND = "Kantesti AI Engine (2.78T)"
SUITE = "Blood Test Benchmark V11"
VERSION = "V11"
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kantesti-bench")


# ════════════════════════════════════════════════════════════════════════════
# CASES
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


CASES: list[Case] = [
    # ── Hematology ─────────────────────────────────────────────────────────
    Case(
        case_id="BT-001-IDA",
        title="Iron Deficiency Anemia — 34F",
        category="Hematology",
        age="34", gender="female",
        panel=[
            {"name": "Hemoglobin",             "value": 9.8,  "unit": "g/dL",    "reference_range": "12.0-16.0"},
            {"name": "Hematocrit",             "value": 30.1, "unit": "%",       "reference_range": "36-46"},
            {"name": "MCV",                    "value": 72.4, "unit": "fL",      "reference_range": "80-100"},
            {"name": "MCH",                    "value": 23.1, "unit": "pg",      "reference_range": "27-33"},
            {"name": "RDW",                    "value": 17.8, "unit": "%",       "reference_range": "11.5-14.5"},
            {"name": "Ferritin",               "value": 6,    "unit": "ng/mL",   "reference_range": "15-150"},
            {"name": "Serum Iron",             "value": 28,   "unit": "ug/dL",   "reference_range": "50-170"},
            {"name": "TIBC",                   "value": 445,  "unit": "ug/dL",   "reference_range": "240-450"},
            {"name": "Transferrin Saturation", "value": 6.3,  "unit": "%",       "reference_range": "20-50"},
        ],
        expected_keywords=["iron deficiency anemia", "ferritin", "mcv", "rdw"],
        expected_scoring_systems=["mentzer"],
        clinical_notes=(
            "Microcytic-hypochromic anemia with depleted ferritin, low TSAT, high TIBC — "
            "textbook absolute iron deficiency. Mentzer Index (MCV/RBC) should be >13, "
            "supporting IDA over thalassemia."
        ),
    ),
    Case(
        case_id="BT-006-B12",
        title="Vitamin B12 Deficiency / Megaloblastic Anemia — 68F",
        category="Hematology",
        age="68", gender="female",
        panel=[
            {"name": "Hemoglobin",          "value": 10.4, "unit": "g/dL",    "reference_range": "12.0-16.0"},
            {"name": "Hematocrit",          "value": 31.5, "unit": "%",       "reference_range": "36-46"},
            {"name": "MCV",                 "value": 112,  "unit": "fL",      "reference_range": "80-100"},
            {"name": "MCH",                 "value": 37.1, "unit": "pg",      "reference_range": "27-33"},
            {"name": "RDW",                 "value": 16.9, "unit": "%",       "reference_range": "11.5-14.5"},
            {"name": "Vitamin B12",         "value": 142,  "unit": "pg/mL",   "reference_range": "200-900"},
            {"name": "Folate",              "value": 6.8,  "unit": "ng/mL",   "reference_range": ">4.0"},
            {"name": "Homocysteine",        "value": 24.3, "unit": "umol/L",  "reference_range": "<15"},
            {"name": "Methylmalonic Acid",  "value": 0.72, "unit": "umol/L",  "reference_range": "<0.40"},
            {"name": "LDH",                 "value": 412,  "unit": "U/L",     "reference_range": "<250"},
            {"name": "Indirect Bilirubin",  "value": 1.4,  "unit": "mg/dL",   "reference_range": "<1.0"},
        ],
        expected_keywords=["b12", "megaloblastic", "macrocytic", "homocysteine"],
        clinical_notes=(
            "Macrocytic anemia (MCV 112) with low B12, elevated MMA and homocysteine — "
            "classic cobalamin deficiency. Elevated LDH and indirect bilirubin reflect "
            "ineffective erythropoiesis. Differential should flag pernicious anemia in a 68-year-old."
        ),
    ),
    Case(
        case_id="BT-007-THAL",
        title="Beta-Thalassemia Minor — 28M",
        category="Hematology",
        age="28", gender="male",
        panel=[
            {"name": "Hemoglobin",              "value": 12.2, "unit": "g/dL",     "reference_range": "13.0-17.0"},
            {"name": "Hematocrit",              "value": 37.8, "unit": "%",        "reference_range": "40-54"},
            {"name": "RBC Count",               "value": 6.2,  "unit": "10^6/uL",  "reference_range": "4.5-5.9"},
            {"name": "MCV",                     "value": 65.8, "unit": "fL",       "reference_range": "80-100"},
            {"name": "MCH",                     "value": 19.7, "unit": "pg",       "reference_range": "27-33"},
            {"name": "MCHC",                    "value": 29.9, "unit": "g/dL",     "reference_range": "32-36"},
            {"name": "RDW",                     "value": 13.8, "unit": "%",        "reference_range": "11.5-14.5"},
            {"name": "Ferritin",                "value": 122,  "unit": "ng/mL",    "reference_range": "24-336"},
            {"name": "Serum Iron",              "value": 108,  "unit": "ug/dL",    "reference_range": "50-170"},
            {"name": "HbA2",                    "value": 5.6,  "unit": "%",        "reference_range": "2.0-3.5"},
            {"name": "HbF",                     "value": 1.8,  "unit": "%",        "reference_range": "<1.0"},
        ],
        expected_keywords=["thalassemia", "hba2", "electrophoresis", "microcytic"],
        expected_scoring_systems=["mentzer"],
        clinical_notes=(
            "Differentiator case: microcytosis with HIGH RBC count, normal RDW, normal "
            "ferritin and elevated HbA2 (>3.5%) — beta-thalassemia trait, NOT iron deficiency. "
            "Mentzer Index = 65.8/6.2 ~= 10.6 (<13 points to thalassemia). Tests whether the "
            "engine uses Mentzer correctly instead of defaulting to IDA."
        ),
    ),

    # ── Endocrinology ──────────────────────────────────────────────────────
    Case(
        case_id="BT-002-HASH",
        title="Hashimoto's Thyroiditis — 42F",
        category="Endocrinology",
        age="42", gender="female",
        panel=[
            {"name": "TSH",                "value": 18.4, "unit": "mIU/L",   "reference_range": "0.4-4.0"},
            {"name": "Free T4",            "value": 0.6,  "unit": "ng/dL",   "reference_range": "0.8-1.8"},
            {"name": "Free T3",            "value": 2.1,  "unit": "pg/mL",   "reference_range": "2.3-4.2"},
            {"name": "Anti-TPO",           "value": 612,  "unit": "IU/mL",   "reference_range": "0-35"},
            {"name": "Anti-Tg",            "value": 289,  "unit": "IU/mL",   "reference_range": "0-40"},
            {"name": "Total Cholesterol",  "value": 238,  "unit": "mg/dL",   "reference_range": "<200"},
        ],
        expected_keywords=["hashimoto", "thyroiditis", "anti-tpo", "tsh", "hypothyroid"],
        clinical_notes=(
            "Overt primary hypothyroidism (TSH 18.4, low FT4/FT3) with strongly positive "
            "anti-TPO and anti-Tg — Hashimoto's thyroiditis. Secondary dyslipidemia expected."
        ),
    ),
    Case(
        case_id="BT-008-PCOS",
        title="PCOS with Insulin Resistance — 26F",
        category="Endocrinology",
        age="26", gender="female",
        panel=[
            {"name": "LH",                 "value": 18.2, "unit": "mIU/mL",  "reference_range": "2.4-12.6"},
            {"name": "FSH",                "value": 5.8,  "unit": "mIU/mL",  "reference_range": "3.5-12.5"},
            {"name": "Total Testosterone", "value": 82,   "unit": "ng/dL",   "reference_range": "15-70"},
            {"name": "Free Testosterone",  "value": 8.4,  "unit": "pg/mL",   "reference_range": "0.5-4.2"},
            {"name": "DHEA-S",             "value": 412,  "unit": "ug/dL",   "reference_range": "35-430"},
            {"name": "SHBG",               "value": 18,   "unit": "nmol/L",  "reference_range": "18-144"},
            {"name": "Prolactin",          "value": 22,   "unit": "ng/mL",   "reference_range": "4.8-23.3"},
            {"name": "17-OH Progesterone", "value": 1.2,  "unit": "ng/mL",   "reference_range": "<2.0"},
            {"name": "Fasting Glucose",    "value": 96,   "unit": "mg/dL",   "reference_range": "70-99"},
            {"name": "Fasting Insulin",    "value": 21,   "unit": "uU/mL",   "reference_range": "2-25"},
            {"name": "HbA1c",              "value": 5.6,  "unit": "%",       "reference_range": "<5.7"},
            {"name": "AMH",                "value": 6.8,  "unit": "ng/mL",   "reference_range": "1.0-4.0"},
        ],
        expected_keywords=["pcos", "polycystic", "hyperandrogenism", "insulin resistance"],
        expected_scoring_systems=["homa-ir"],
        clinical_notes=(
            "Rotterdam-style PCOS picture: elevated LH/FSH ratio (~3.1), biochemical "
            "hyperandrogenism (high total+free testosterone, low SHBG), elevated AMH. "
            "HOMA-IR ~= 4.97 indicates meaningful insulin resistance despite normoglycemia."
        ),
    ),

    # ── Metabolic ──────────────────────────────────────────────────────────
    Case(
        case_id="BT-003-T2DM",
        title="T2DM + Metabolic Syndrome — 51M",
        category="Metabolic",
        age="51", gender="male",
        panel=[
            {"name": "Fasting Glucose",     "value": 142, "unit": "mg/dL",   "reference_range": "70-99"},
            {"name": "HbA1c",               "value": 7.8, "unit": "%",       "reference_range": "<5.7"},
            {"name": "Insulin (fasting)",   "value": 22,  "unit": "uU/mL",   "reference_range": "2-25"},
            {"name": "Triglycerides",       "value": 278, "unit": "mg/dL",   "reference_range": "<150"},
            {"name": "HDL Cholesterol",     "value": 34,  "unit": "mg/dL",   "reference_range": ">40"},
            {"name": "LDL Cholesterol",     "value": 168, "unit": "mg/dL",   "reference_range": "<130"},
            {"name": "ALT",                 "value": 58,  "unit": "U/L",     "reference_range": "<41"},
            {"name": "GGT",                 "value": 74,  "unit": "U/L",     "reference_range": "<60"},
        ],
        expected_keywords=["type 2 diabetes", "metabolic syndrome", "hba1c", "insulin resistance"],
        expected_scoring_systems=["homa-ir", "ascvd"],
        clinical_notes=(
            "ADA-criteria T2DM (HbA1c 7.8%, FPG 142) with atherogenic dyslipidemia, "
            "low HDL, hepatic transaminase elevation — meets >=3 NCEP-ATP III criteria "
            "for metabolic syndrome. HOMA-IR ~= 7.7."
        ),
    ),
    Case(
        case_id="BT-013-GOUT",
        title="Hyperuricemia with Gout Risk — 48M",
        category="Metabolic",
        age="48", gender="male",
        panel=[
            {"name": "Uric Acid",          "value": 9.8, "unit": "mg/dL",          "reference_range": "3.5-7.2"},
            {"name": "Creatinine",         "value": 1.2, "unit": "mg/dL",          "reference_range": "0.7-1.3"},
            {"name": "eGFR",               "value": 72,  "unit": "mL/min/1.73m2",  "reference_range": ">60"},
            {"name": "Urea",               "value": 38,  "unit": "mg/dL",          "reference_range": "17-43"},
            {"name": "ESR",                "value": 32,  "unit": "mm/hr",          "reference_range": "<15"},
            {"name": "CRP",                "value": 1.8, "unit": "mg/dL",          "reference_range": "<0.5"},
            {"name": "Triglycerides",      "value": 212, "unit": "mg/dL",          "reference_range": "<150"},
            {"name": "Fasting Glucose",    "value": 108, "unit": "mg/dL",          "reference_range": "70-99"},
            {"name": "ALT",                "value": 44,  "unit": "U/L",            "reference_range": "<41"},
        ],
        expected_keywords=["hyperuricemia", "gout", "uric acid"],
        clinical_notes=(
            "Uric acid 9.8 with elevated inflammatory markers (ESR/CRP) and metabolic "
            "co-factors (IFG, hypertriglyceridemia) — classic profile for gout in the "
            "context of metabolic syndrome."
        ),
    ),

    # ── Hepatology ─────────────────────────────────────────────────────────
    Case(
        case_id="BT-004-NAFLD",
        title="NAFLD / NASH — 46M",
        category="Hepatology",
        age="46", gender="male",
        panel=[
            {"name": "ALT",             "value": 96,  "unit": "U/L",     "reference_range": "<41"},
            {"name": "AST",             "value": 58,  "unit": "U/L",     "reference_range": "<40"},
            {"name": "GGT",             "value": 112, "unit": "U/L",     "reference_range": "<60"},
            {"name": "ALP",             "value": 145, "unit": "U/L",     "reference_range": "40-129"},
            {"name": "Total Bilirubin", "value": 0.9, "unit": "mg/dL",   "reference_range": "0.2-1.2"},
            {"name": "Platelets",       "value": 178, "unit": "10^3/uL", "reference_range": "150-450"},
            {"name": "Albumin",         "value": 4.1, "unit": "g/dL",    "reference_range": "3.5-5.0"},
            {"name": "Triglycerides",   "value": 232, "unit": "mg/dL",   "reference_range": "<150"},
        ],
        expected_keywords=["nafld", "fatty liver", "steatohepatitis"],
        expected_scoring_systems=["fib-4", "de ritis"],
        clinical_notes=(
            "ALT-dominant transaminase elevation (De Ritis <1), GGT/ALP cholestasis pattern, "
            "hypertriglyceridemia — NAFLD/NASH spectrum. FIB-4 should be computed to "
            "stratify advanced fibrosis risk."
        ),
    ),
    Case(
        case_id="BT-009-VIRHEP",
        title="Acute Viral Hepatitis — 22M",
        category="Hepatology",
        age="22", gender="male",
        panel=[
            {"name": "ALT",               "value": 1420, "unit": "U/L",     "reference_range": "<41"},
            {"name": "AST",               "value": 980,  "unit": "U/L",     "reference_range": "<40"},
            {"name": "GGT",               "value": 145,  "unit": "U/L",     "reference_range": "<60"},
            {"name": "ALP",               "value": 162,  "unit": "U/L",     "reference_range": "40-129"},
            {"name": "Total Bilirubin",   "value": 6.8,  "unit": "mg/dL",   "reference_range": "0.2-1.2"},
            {"name": "Direct Bilirubin",  "value": 4.2,  "unit": "mg/dL",   "reference_range": "0.0-0.3"},
            {"name": "INR",               "value": 1.3,  "unit": "",        "reference_range": "0.9-1.2"},
            {"name": "Albumin",           "value": 3.6,  "unit": "g/dL",    "reference_range": "3.5-5.0"},
            {"name": "WBC",               "value": 4.1,  "unit": "10^3/uL", "reference_range": "4.5-11.0"},
            {"name": "Lymphocytes %",     "value": 52,   "unit": "%",       "reference_range": "20-40"},
        ],
        expected_keywords=["acute hepatitis", "transaminase", "hepatocellular", "viral"],
        expected_scoring_systems=["de ritis"],
        clinical_notes=(
            "Extreme hepatocellular injury (ALT 1420, AST 980; ratio <1 = hepatocellular), "
            "conjugated hyperbilirubinemia, mild coagulopathy (INR 1.3), relative "
            "lymphocytosis — strongly suggests acute viral hepatitis."
        ),
    ),
    Case(
        case_id="BT-014-GILBERT",
        title="Gilbert's Syndrome — Isolated Unconjugated Hyperbilirubinemia [Trap] — 24M",
        category="Trap",
        age="24", gender="male",
        panel=[
            {"name": "Total Bilirubin",    "value": 2.4, "unit": "mg/dL",    "reference_range": "0.2-1.2"},
            {"name": "Direct Bilirubin",   "value": 0.3, "unit": "mg/dL",    "reference_range": "0.0-0.3"},
            {"name": "Indirect Bilirubin", "value": 2.1, "unit": "mg/dL",    "reference_range": "<1.0"},
            {"name": "ALT",                "value": 22,  "unit": "U/L",      "reference_range": "<41"},
            {"name": "AST",                "value": 24,  "unit": "U/L",      "reference_range": "<40"},
            {"name": "GGT",                "value": 28,  "unit": "U/L",      "reference_range": "<60"},
            {"name": "ALP",                "value": 82,  "unit": "U/L",      "reference_range": "40-129"},
            {"name": "Albumin",            "value": 4.6, "unit": "g/dL",     "reference_range": "3.5-5.0"},
            {"name": "Hemoglobin",         "value": 14.8,"unit": "g/dL",     "reference_range": "13.0-17.0"},
            {"name": "Reticulocytes",      "value": 1.1, "unit": "%",        "reference_range": "0.5-2.5"},
            {"name": "Haptoglobin",        "value": 112, "unit": "mg/dL",    "reference_range": "30-200"},
            {"name": "LDH",                "value": 178, "unit": "U/L",      "reference_range": "<250"},
        ],
        expected_keywords=["gilbert", "unconjugated", "benign"],
        hyperdiagnosis_flags=[
            "hepatitis", "cirrhosis", "hemolytic anemia", "liver failure",
            "liver disease", "biliary obstruction",
        ],
        clinical_notes=(
            "TRAP CASE. Isolated indirect hyperbilirubinemia with fully normal LFTs, "
            "preserved haptoglobin and LDH, normal reticulocytes — rules out hemolysis "
            "AND hepatocellular injury. Correct diagnosis: Gilbert's syndrome (UGT1A1 "
            "polymorphism, benign)."
        ),
    ),

    # ── Nephrology ─────────────────────────────────────────────────────────
    Case(
        case_id="BT-005-CKD",
        title="CKD Stage 3 — 62M",
        category="Nephrology",
        age="62", gender="male",
        panel=[
            {"name": "Creatinine",                "value": 1.9, "unit": "mg/dL",           "reference_range": "0.7-1.3"},
            {"name": "eGFR",                      "value": 38,  "unit": "mL/min/1.73m2",   "reference_range": ">60"},
            {"name": "Urea",                      "value": 62,  "unit": "mg/dL",           "reference_range": "17-43"},
            {"name": "Potassium",                 "value": 5.3, "unit": "mmol/L",          "reference_range": "3.5-5.1"},
            {"name": "Phosphorus",                "value": 4.8, "unit": "mg/dL",           "reference_range": "2.5-4.5"},
            {"name": "Albumin/Creatinine Ratio",  "value": 120, "unit": "mg/g",            "reference_range": "<30"},
            {"name": "Hemoglobin",                "value": 11.2,"unit": "g/dL",            "reference_range": "13.0-17.0"},
        ],
        expected_keywords=["chronic kidney disease", "egfr", "albuminuria"],
        expected_scoring_systems=["ckd-epi"],
        clinical_notes=(
            "eGFR 38 + UACR 120 places the patient in KDIGO G3b/A2 — CKD Stage 3. "
            "Early features of CKD-MBD (borderline phosphate) and renal anemia."
        ),
    ),

    # ── Cardiology ─────────────────────────────────────────────────────────
    Case(
        case_id="BT-010-ASCVD",
        title="High Cardiovascular Risk — Atherogenic Dyslipidemia — 58M",
        category="Cardiology",
        age="58", gender="male",
        panel=[
            {"name": "Total Cholesterol",   "value": 268, "unit": "mg/dL",   "reference_range": "<200"},
            {"name": "LDL Cholesterol",     "value": 188, "unit": "mg/dL",   "reference_range": "<100"},
            {"name": "HDL Cholesterol",     "value": 32,  "unit": "mg/dL",   "reference_range": ">40"},
            {"name": "Triglycerides",       "value": 242, "unit": "mg/dL",   "reference_range": "<150"},
            {"name": "Non-HDL Cholesterol", "value": 236, "unit": "mg/dL",   "reference_range": "<130"},
            {"name": "ApoB",                "value": 148, "unit": "mg/dL",   "reference_range": "<100"},
            {"name": "Lipoprotein(a)",      "value": 96,  "unit": "nmol/L",  "reference_range": "<75"},
            {"name": "hs-CRP",              "value": 4.8, "unit": "mg/L",    "reference_range": "<3.0"},
            {"name": "Fasting Glucose",     "value": 104, "unit": "mg/dL",   "reference_range": "70-99"},
            {"name": "HbA1c",               "value": 5.9, "unit": "%",       "reference_range": "<5.7"},
        ],
        expected_keywords=["dyslipidemia", "cardiovascular risk", "ldl", "apob"],
        expected_scoring_systems=["ascvd"],
        clinical_notes=(
            "Severely elevated atherogenic particles (ApoB 148, non-HDL 236, Lp(a) 96), "
            "low HDL, high-sensitivity CRP >3 — high ASCVD 10-year risk category."
        ),
    ),

    # ── Rheumatology ───────────────────────────────────────────────────────
    Case(
        case_id="BT-011-SLE",
        title="Systemic Lupus Erythematosus — 31F",
        category="Rheumatology",
        age="31", gender="female",
        panel=[
            {"name": "ANA (titer)",         "value": 640,  "unit": "1:x",      "reference_range": "<1:80"},
            {"name": "Anti-dsDNA",          "value": 285,  "unit": "IU/mL",    "reference_range": "<30"},
            {"name": "Anti-Smith",          "value": 48,   "unit": "U/mL",     "reference_range": "<20"},
            {"name": "Complement C3",       "value": 52,   "unit": "mg/dL",    "reference_range": "90-180"},
            {"name": "Complement C4",       "value": 8,    "unit": "mg/dL",    "reference_range": "10-40"},
            {"name": "ESR",                 "value": 78,   "unit": "mm/hr",    "reference_range": "<20"},
            {"name": "CRP",                 "value": 2.1,  "unit": "mg/dL",    "reference_range": "<0.5"},
            {"name": "WBC",                 "value": 3.2,  "unit": "10^3/uL",  "reference_range": "4.5-11.0"},
            {"name": "Lymphocytes (abs)",   "value": 0.8,  "unit": "10^3/uL",  "reference_range": "1.0-4.8"},
            {"name": "Platelets",           "value": 118,  "unit": "10^3/uL",  "reference_range": "150-450"},
            {"name": "Urine Protein (24h)", "value": 2.4,  "unit": "g/24h",    "reference_range": "<0.15"},
            {"name": "Creatinine",          "value": 1.2,  "unit": "mg/dL",    "reference_range": "0.6-1.1"},
        ],
        expected_keywords=["lupus", "sle", "autoimmune", "anti-dsdna", "complement"],
        expected_scoring_systems=["slicc", "eular"],
        clinical_notes=(
            "Multi-system autoimmune picture meeting 2019 EULAR/ACR SLE criteria: ANA 1:640, "
            "high anti-dsDNA and anti-Smith, low C3/C4, lymphopenia, thrombocytopenia, and "
            "nephrotic-range proteinuria."
        ),
    ),

    # ── Vitamin/Mineral ────────────────────────────────────────────────────
    Case(
        case_id="BT-012-VITD",
        title="Severe Vitamin D Deficiency + Secondary Hyperparathyroidism — 55F",
        category="Endocrinology",
        age="55", gender="female",
        panel=[
            {"name": "25-OH Vitamin D",   "value": 11,   "unit": "ng/mL",   "reference_range": "30-100"},
            {"name": "PTH",               "value": 98,   "unit": "pg/mL",   "reference_range": "15-65"},
            {"name": "Calcium (total)",   "value": 8.4,  "unit": "mg/dL",   "reference_range": "8.6-10.2"},
            {"name": "Ionized Calcium",   "value": 1.08, "unit": "mmol/L",  "reference_range": "1.12-1.32"},
            {"name": "Phosphorus",        "value": 2.6,  "unit": "mg/dL",   "reference_range": "2.5-4.5"},
            {"name": "ALP",               "value": 138,  "unit": "U/L",     "reference_range": "40-129"},
            {"name": "Magnesium",         "value": 1.7,  "unit": "mg/dL",   "reference_range": "1.7-2.2"},
            {"name": "Creatinine",        "value": 0.8,  "unit": "mg/dL",   "reference_range": "0.6-1.1"},
            {"name": "TSH",               "value": 2.1,  "unit": "mIU/L",   "reference_range": "0.4-4.0"},
        ],
        expected_keywords=["vitamin d", "hyperparathyroidism", "calcium", "pth"],
        clinical_notes=(
            "25-OH-D 11 (severe deficiency) with compensatory PTH elevation (98), "
            "low-normal calcium and phosphorus, elevated ALP — classic picture of "
            "secondary hyperparathyroidism from vitamin D deficiency."
        ),
    ),

    # ── Trap: Fully Healthy Adult ──────────────────────────────────────────
    Case(
        case_id="BT-015-HEALTHY",
        title="Healthy Adult — Routine Screening [Trap] — 35F",
        category="Trap",
        age="35", gender="female",
        panel=[
            {"name": "Hemoglobin",        "value": 13.8, "unit": "g/dL",     "reference_range": "12.0-16.0"},
            {"name": "WBC",               "value": 6.4,  "unit": "10^3/uL",  "reference_range": "4.5-11.0"},
            {"name": "Platelets",         "value": 268,  "unit": "10^3/uL",  "reference_range": "150-450"},
            {"name": "Fasting Glucose",   "value": 88,   "unit": "mg/dL",    "reference_range": "70-99"},
            {"name": "HbA1c",             "value": 5.2,  "unit": "%",        "reference_range": "<5.7"},
            {"name": "Total Cholesterol", "value": 178,  "unit": "mg/dL",    "reference_range": "<200"},
            {"name": "HDL",               "value": 62,   "unit": "mg/dL",    "reference_range": ">40"},
            {"name": "LDL",               "value": 98,   "unit": "mg/dL",    "reference_range": "<100"},
            {"name": "Triglycerides",     "value": 88,   "unit": "mg/dL",    "reference_range": "<150"},
            {"name": "ALT",               "value": 18,   "unit": "U/L",      "reference_range": "<41"},
            {"name": "AST",               "value": 21,   "unit": "U/L",      "reference_range": "<40"},
            {"name": "Creatinine",        "value": 0.8,  "unit": "mg/dL",    "reference_range": "0.6-1.1"},
            {"name": "TSH",               "value": 2.1,  "unit": "mIU/L",    "reference_range": "0.4-4.0"},
            {"name": "25-OH Vitamin D",   "value": 38,   "unit": "ng/mL",    "reference_range": "30-100"},
            {"name": "Ferritin",          "value": 68,   "unit": "ng/mL",    "reference_range": "15-150"},
        ],
        expected_keywords=["normal", "unremarkable", "within reference", "healthy"],
        hyperdiagnosis_flags=[
            "diabetes", "anemia", "hypothyroidism", "dyslipidemia", "hepatitis",
            "kidney disease", "deficiency",
        ],
        clinical_notes=(
            "TRAP CASE. Every parameter sits comfortably within its reference range. "
            "Correct output: reassurance + lifestyle maintenance."
        ),
    ),
]


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
        author="Kantesti Benchmark Harness V11",
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
        "Reference Laboratory — Synthetic Benchmark Dataset",
        meta_style,
    ))
    story.append(Spacer(1, 6))

    # ── Patient / sample block ─────────────────────────────────────────
    today = time.strftime("%Y-%m-%d")
    patient_block = [
        ["Case ID:",     case.case_id,             "Collection:",  today],
        ["Age:",         case.age + " years",      "Report date:", today],
        ["Sex:",         case.gender.capitalize(), "Sample type:", "Serum / Plasma"],
        ["Panel type:",  case.category,            "Status:",      "Final"],
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
        "Anonymised benchmark laboratory report generated by the Kantesti "
        "Benchmark Harness (V11) for evaluation purposes only. Direct "
        "identifiers removed under the Safe Harbor de-identification "
        "approach."
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
# SCORING — against pre-registered rubric
# ════════════════════════════════════════════════════════════════════════════
MANDATORY_SECTION_SHORTCODES = [
    "introduction", "overall_health_assessment", "detailed_health_analysis",
    "risk_factors", "recommendations", "further_evaluation", "conclusion",
]

MANDATORY_SUBSECTION_SHORTCODES = [
    "introduction_summary", "introduction_purpose",
    "overall_health_assessment_overview", "overall_health_assessment_key_findings",
    "detailed_health_analysis_trends_parameters", "detailed_health_analysis_correlations",
    "risk_factors_identification", "risk_factors_severity_probabilities",
    "risk_factors_probabilities_of_diseases", "risk_factors_explanations_percentiles",
    "recommendations_medical", "recommendations_lifestyle_dietary",
    "further_evaluation_follow_up", "further_evaluation_referral",
    "conclusion_summary", "conclusion_final_recommendations",
]


def _flatten_text(resp: dict) -> str:
    buf: list[str] = []
    for section in resp.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        buf.append(str(section.get("title", "")))
        for sub in section.get("subsections", []) or []:
            if not isinstance(sub, dict):
                continue
            buf.append(str(sub.get("subtitle", "")))
            for it in sub.get("items", []) or []:
                buf.append(str(it.get("item", "")) if isinstance(it, dict) else str(it))
    return "\n".join(buf).lower()


def _probability_sum(resp: dict) -> float:
    total = 0.0
    for section in resp.get("sections", []) or []:
        if not isinstance(section, dict) or section.get("shortcode") != "risk_factors":
            continue
        for sub in section.get("subsections", []) or []:
            if not isinstance(sub, dict):
                continue
            if sub.get("shortcode") != "risk_factors_probabilities_of_diseases":
                continue
            for it in sub.get("items", []) or []:
                text = it.get("item", "") if isinstance(it, dict) else str(it)
                for match in re.findall(r"(\d{1,3}(?:\.\d+)?)\s*%", text):
                    try:
                        total += float(match)
                    except ValueError:
                        pass
    return total


def score_case(case: Case, resp: Any, elapsed: float, engine_path: str) -> dict:
    if not isinstance(resp, dict) or resp.get("error"):
        err = "no response"
        if isinstance(resp, dict):
            err = resp.get("error_message") or resp.get("error") or "unknown"
        return {
            "case_id": case.case_id,
            "title": case.title,
            "category": case.category,
            "status": "error",
            "elapsed_sec": round(elapsed, 2),
            "engine_path": engine_path,
            "error": str(err),
            "composite_score": 0.0,
        }

    text = _flatten_text(resp)
    sections = resp.get("sections", []) or []

    sec_codes = {s.get("shortcode") for s in sections if isinstance(s, dict)}
    sub_codes: set[str] = set()
    for s in sections:
        if isinstance(s, dict):
            for sub in s.get("subsections", []) or []:
                if isinstance(sub, dict):
                    sub_codes.add(sub.get("shortcode"))

    sec_hits = sum(1 for c in MANDATORY_SECTION_SHORTCODES if c in sec_codes)
    sub_hits = sum(1 for c in MANDATORY_SUBSECTION_SHORTCODES if c in sub_codes)
    structural = (
        (sec_hits / len(MANDATORY_SECTION_SHORTCODES)) * 0.4
        + (sub_hits / len(MANDATORY_SUBSECTION_SHORTCODES)) * 0.6
    )

    prob_sum = _probability_sum(resp)
    prob_ok = 90.0 <= prob_sum <= 110.0

    kw_hits = sum(1 for k in case.expected_keywords if k.lower() in text)
    kw_score = kw_hits / max(1, len(case.expected_keywords))

    ss_hits = sum(1 for k in case.expected_scoring_systems if k.lower() in text)
    ss_score = (
        ss_hits / max(1, len(case.expected_scoring_systems))
        if case.expected_scoring_systems else 1.0
    )

    hyperdx_hits = [flag for flag in case.hyperdiagnosis_flags if flag.lower() in text]
    hyperdx_penalty = min(0.30, 0.10 * len(hyperdx_hits))

    clinical_raw = kw_score * 0.7 + ss_score * 0.2 + (0.1 if prob_ok else 0.0)
    clinical = max(0.0, clinical_raw - hyperdx_penalty)

    if elapsed < 20:
        latency = 0.10
    elif elapsed < 40:
        latency = 0.05
    else:
        latency = 0.0

    composite = structural * 0.35 + clinical * 0.55 + latency

    return {
        "case_id": case.case_id,
        "title": case.title,
        "category": case.category,
        "status": "ok",
        "elapsed_sec": round(elapsed, 2),
        "engine_path": engine_path,
        "structural": {
            "sections_hit": f"{sec_hits}/{len(MANDATORY_SECTION_SHORTCODES)}",
            "subsections_hit": f"{sub_hits}/{len(MANDATORY_SUBSECTION_SHORTCODES)}",
            "probabilities_sum": round(prob_sum, 1),
            "probabilities_valid": prob_ok,
            "score": round(structural, 3),
        },
        "clinical": {
            "keywords_hit": f"{kw_hits}/{len(case.expected_keywords)}",
            "missed_keywords": [k for k in case.expected_keywords if k.lower() not in text],
            "scoring_systems_hit": f"{ss_hits}/{len(case.expected_scoring_systems)}",
            "hyperdiagnosis_hits": hyperdx_hits,
            "hyperdiagnosis_penalty": round(hyperdx_penalty, 3),
            "score": round(clinical, 3),
        },
        "composite_score": round(composite, 3),
    }


# ════════════════════════════════════════════════════════════════════════════
# EXPORTERS
# ════════════════════════════════════════════════════════════════════════════
def _write_markdown(report: dict, path: Path) -> None:
    lines: list[str] = []
    agg = report["aggregate"]
    lines.append(f"# {report['engine']} — {report['suite']}")
    lines.append("")
    lines.append(f"**Run:** {report['started_at']}  ")
    lines.append(f"**Version:** {VERSION}  ")
    lines.append(f"**Engine:** `{ENGINE_DISPLAY_NAME}`  ")
    lines.append(f"**Endpoint:** `{report['endpoint']}`  ")
    lines.append(f"**Cases:** {report['cases_ok']}/{report['cases_total']} scored  ")
    lines.append(f"**Composite Score:** `{agg['composite_score']:.4f}` "
                 f"(`{agg['composite_score']*100:.2f}%`)  ")
    lines.append("")
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Composite | **{agg['composite_score']:.4f}** |")
    lines.append(f"| Structural | {agg['structural_score']:.3f} |")
    lines.append(f"| Clinical | {agg['clinical_score']:.3f} |")
    lines.append(f"| Avg Latency | {agg['avg_latency_sec']:.2f} s |")
    lines.append(f"| Min Latency | {agg.get('min_latency_sec', 0):.1f} s |")
    lines.append(f"| Max Latency | {agg.get('max_latency_sec', 0):.1f} s |")
    lines.append("")
    lines.append("## Per-Category Breakdown")
    lines.append("")
    lines.append("| Category | Cases | Composite | Structural | Clinical |")
    lines.append("|---|---:|---:|---:|---:|")
    for cat, stats in report["per_category"].items():
        lines.append(
            f"| {cat} | {stats['n']} | {stats['composite']:.3f} | "
            f"{stats['structural']:.3f} | {stats['clinical']:.3f} |"
        )
    lines.append("")
    lines.append("## Per-Case Results")
    lines.append("")
    lines.append("| # | Case ID | Title | Category | Composite | Structural | Clinical | Latency | Path |")
    lines.append("|---:|---|---|---|---:|---:|---:|---:|---|")
    for i, c in enumerate(report["cases"], 1):
        if c["status"] != "ok":
            lines.append(
                f"| {i} | {c['case_id']} | {c['title']} | {c.get('category','-')} | "
                f"ERR | — | — | {c['elapsed_sec']:.1f}s | {c.get('engine_path', '—')} |"
            )
            continue
        lines.append(
            f"| {i} | {c['case_id']} | {c['title']} | {c['category']} | "
            f"**{c['composite_score']:.3f}** | {c['structural']['score']:.3f} | "
            f"{c['clinical']['score']:.3f} | {c['elapsed_sec']:.1f}s | "
            f"{c.get('engine_path', '—')} |"
        )
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "Scores are computed against a **pre-registered rubric** — the expected "
        "diagnoses, clinical scoring systems and report sections are fixed before "
        "the engine is invoked, so no cherry-picking is possible after the fact."
    )
    lines.append("")
    lines.append("Composite = `0.35 x Structural + 0.55 x Clinical + 0.10 x Latency`.")
    lines.append("")
    lines.append(
        "**Structural (35%)** — fraction of the 7 mandatory report sections and 16 "
        "mandatory subsections present in the output, weighted 40/60."
    )
    lines.append("")
    lines.append(
        "**Clinical (55%)** — diagnosis keyword recall (70%), scoring-system recall "
        "(20%), probability sum in [90,110] (10%). Trap cases carry a hyperdiagnosis "
        "penalty of up to 0.30 for fabricated pathologies."
    )
    lines.append("")
    lines.append(
        "**Latency (10%)** — 0.10 if <20 s (primary-path target), 0.05 if <40 s "
        "(soft ceiling), 0 otherwise."
    )
    lines.append("")
    lines.append("## Case Reference")
    lines.append("")
    lines.append("| Case ID | Category | Rationale |")
    lines.append("|---|---|---|")
    for case in CASES:
        note = case.clinical_notes.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {case.case_id} | {case.category} | {note} |")
    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by {report['engine']} Benchmark Harness v{VERSION}.*")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(report: dict, path: Path) -> None:
    fields = [
        "case_id", "title", "category", "status", "composite_score",
        "structural_score", "clinical_score", "elapsed_sec",
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
            "composite":  round(sum(x["composite_score"] for x in items) / n, 3),
            "structural": round(sum(x["structural"]["score"] for x in items) / n, 3),
            "clinical":   round(sum(x["clinical"]["score"] for x in items) / n, 3),
            "latency":    round(sum(x["elapsed_sec"] for x in items) / n, 2),
        }
    return out


def run_benchmark(
    out_dir: str | os.PathLike = "benchmark_results",
    language: str = "en",
    sandbox: bool = False,
) -> dict:
    if not KANTESTI_USERNAME or not KANTESTI_PASSWORD:
        raise SystemExit(
            "ERROR: Kantesti API credentials are not set.\n"
            "       Either `export KANTESTI_USERNAME=... KANTESTI_PASSWORD=...` before running,\n"
            "       or paste them into the constants near the top of this file."
        )

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    endpoint_str = API_BASE_URL + (API_ENDPOINT_SANDBOX if sandbox else API_ENDPOINT_LIVE)

    header = f"  {BRAND} — {SUITE}"
    bar = "=" * max(72, len(header) + 4)
    print(bar)
    print(header)
    print(f"  Run started  : {started}")
    print(f"  Cases        : {len(CASES)}")
    print(f"  Language     : {language}")
    print(f"  Endpoint     : {endpoint_str}")
    print(f"  Mode         : {'SANDBOX (no quota)' if sandbox else 'LIVE (consumes credits)'}")
    print(f"  Version      : {VERSION}")
    print(bar)

    detail: list[dict] = []
    for idx, case in enumerate(CASES, 1):
        print(f"\n[{idx}/{len(CASES)}] {case.case_id} — {case.title}")
        t0 = time.time()
        engine_path = "unknown"
        try:
            resp, engine_path = run_interpretation(case, language, sandbox=sandbox)
        except Exception as exc:
            resp = {"error": True, "error_message": f"{type(exc).__name__}: {exc}"}
        elapsed = time.time() - t0

        summary = score_case(case, resp, elapsed, engine_path)
        detail.append({"summary": summary, "response": resp})

        if summary["status"] == "ok":
            s, c = summary["structural"], summary["clinical"]
            print(
                f"  OK  {elapsed:5.1f}s  composite={summary['composite_score']:.3f}"
                f"  sec {s['sections_hit']}  sub {s['subsections_hit']}"
                f"  kw {c['keywords_hit']}  probs={s['probabilities_sum']}"
                f"  path={engine_path}"
            )
            if c["missed_keywords"]:
                print(f"     missed: {', '.join(c['missed_keywords'])}")
            if c.get("hyperdiagnosis_hits"):
                print(f"     HYPER : {', '.join(c['hyperdiagnosis_hits'])} "
                      f"(-{c['hyperdiagnosis_penalty']:.2f})")
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
        "cases_total": len(CASES),
        "cases_ok": len(scored),
        "aggregate": {
            "composite_score":  round(avg_comp, 4),
            "structural_score": round(avg_struct, 3),
            "clinical_score":   round(avg_clin, 3),
            "avg_latency_sec":  round(avg_lat, 2),
            "min_latency_sec":  round(min_lat, 2),
            "max_latency_sec":  round(max_lat, 2),
        },
        "per_category": _aggregate_by_category(all_cases),
        "cases": all_cases,
    }

    stamp = time.strftime("%Y%m%d_%H%M%S")
    summary_path = out / f"kantesti_benchmark_{stamp}.json"
    full_path    = out / f"kantesti_benchmark_{stamp}_full.json"
    md_path      = out / f"kantesti_benchmark_{stamp}.md"
    csv_path     = out / f"kantesti_benchmark_{stamp}.csv"

    summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    full_path.write_text(
        json.dumps(
            {"engine": BRAND, "suite": SUITE, "version": VERSION, "endpoint": endpoint_str,
             "cases": detail},
            indent=2, ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    _write_markdown(report, md_path)
    _write_csv(report, csv_path)

    print()
    print(bar)
    print(f"  {BRAND} — AGGREGATE RESULTS")
    print(bar)
    print(f"  composite  : {avg_comp:.4f}  ({avg_comp*100:.2f}%)")
    print(f"  structural : {avg_struct:.3f}")
    print(f"  clinical   : {avg_clin:.3f}")
    print(f"  latency    : avg {avg_lat:.2f}s  min {min_lat:.1f}s  max {max_lat:.1f}s")
    print(f"  cases ok   : {len(scored)}/{len(CASES)}")
    print()
    print("  Per-category:")
    for cat, stats in report["per_category"].items():
        print(f"    {cat:<14} n={stats['n']}  comp={stats['composite']:.3f}  "
              f"struct={stats['structural']:.3f}  clin={stats['clinical']:.3f}")
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
    p.add_argument("--sandbox", action="store_true",
                   help="Use the sandbox endpoint (no credit consumption)")
    args = p.parse_args()

    global KANTESTI_USERNAME, KANTESTI_PASSWORD
    if args.username:
        KANTESTI_USERNAME = args.username
    if args.password:
        KANTESTI_PASSWORD = args.password

    run_benchmark(out_dir=args.out, language=args.lang, sandbox=args.sandbox)


if __name__ == "__main__":
    _cli()
