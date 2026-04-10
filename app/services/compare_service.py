"""
Contract comparison service.
Supports Excel/CSV field-level comparison and semantic clause similarity.
"""

from __future__ import annotations
import io
import logging
from typing import Optional

import pandas as pd

from app.nlp.embeddings import cosine_similarity, embed_text

logger = logging.getLogger(__name__)


# ── Excel / CSV Comparison ────────────────────────────────────────────────────

COMPARE_FIELDS = ["title", "value", "end_date", "buyer", "supplier", "cpv_code"]


def compare_excel_contracts(file1_bytes: bytes, file2_bytes: bytes) -> dict:
    """
    Compare two Excel contract files field by field.
    Expects both files to have a shared 'id' or row-number key.

    Returns a dict with matched rows, mismatches, and summary.
    """
    try:
        df1 = pd.read_excel(io.BytesIO(file1_bytes))
        df2 = pd.read_excel(io.BytesIO(file2_bytes))
    except Exception as e:
        logger.error(f"Excel parse error: {e}")
        raise ValueError(f"Could not parse Excel files: {e}")

    # Normalize column names to lowercase
    df1.columns = [c.lower().strip() for c in df1.columns]
    df2.columns = [c.lower().strip() for c in df2.columns]

    # Try to merge on 'id' or 'no' column, otherwise use row index
    merge_key = "id" if "id" in df1.columns and "id" in df2.columns else None

    if merge_key:
        merged = df1.merge(df2, on=merge_key, suffixes=("_a", "_b"))
    else:
        merged = df1.join(df2, lsuffix="_a", rsuffix="_b")

    mismatches = []
    for _, row in merged.iterrows():
        for field in COMPARE_FIELDS:
            col_a = f"{field}_a"
            col_b = f"{field}_b"
            if col_a in row and col_b in row:
                val_a = str(row[col_a]).strip()
                val_b = str(row[col_b]).strip()
                if val_a != val_b and val_a != "nan" and val_b != "nan":
                    mismatches.append({
                        "field": field,
                        "value_a": val_a,
                        "value_b": val_b,
                    })

    return {
        "rows_compared": len(merged),
        "mismatches": mismatches,
        "match_count": len(merged) - len(mismatches),
    }


# ── Semantic Clause Comparison ────────────────────────────────────────────────

def compare_clause_texts(clause_a: str, clause_b: str) -> dict:
    """
    Compare two clause texts using cosine similarity of their embeddings.

    Returns similarity score and a match verdict.
    """
    try:
        vec_a = embed_text(clause_a)
        vec_b = embed_text(clause_b)
        score = cosine_similarity(vec_a, vec_b)
        return {
            "similarity_score": round(score, 4),
            "match": score >= 0.85,
            "verdict": "Near-identical" if score >= 0.95
                       else "Very similar" if score >= 0.85
                       else "Partially similar" if score >= 0.6
                       else "Different",
        }
    except Exception as e:
        logger.error(f"Clause comparison error: {e}")
        raise
