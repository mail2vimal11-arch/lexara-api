"""
Advanced training data — Part 3: CUAD + MAUD dataset integration.
Generates training examples from HuggingFace datasets at Kaggle runtime.
This module provides the loader function called from the Kaggle notebook.
"""


def generate_cuad_training_data(max_examples=200):
    """
    Load CUAD dataset from HuggingFace and generate clause classification
    training examples. Run this on Kaggle (needs internet + datasets library).

    CUAD covers 41 clause categories across 500+ real commercial contracts.
    """
    from datasets import load_dataset
    import json

    try:
        ds = load_dataset("unitaryai/cuad", split="train")
    except Exception:
        return []

    # CUAD's 41 clause categories
    CUAD_LABELS = [
        "Document Name", "Parties", "Agreement Date", "Effective Date",
        "Expiration Date", "Renewal Term", "Notice Period To Terminate Renewal",
        "Governing Law", "Most Favored Nation", "Non-Compete",
        "Exclusivity", "No-Solicit Of Customers", "No-Solicit Of Employees",
        "Non-Disparagement", "Termination For Convenience",
        "Rofr/Rofo/Rofn", "Change Of Control", "Anti-Assignment",
        "Revenue/Profit Sharing", "Price Restrictions",
        "Minimum Commitment", "Volume Restriction", "Ip Ownership Assignment",
        "Joint Ip Ownership", "License Grant", "Non-Transferable License",
        "Affiliate License-Loss", "Unlimited/All-You-Can-Eat-License",
        "Irrevocable Or Perpetual License", "Source Code Escrow",
        "Post-Termination Services", "Audit Rights", "Uncapped Liability",
        "Cap On Liability", "Liquidated Damages", "Warranty Duration",
        "Insurance", "Covenant Not To Sue", "Third Party Beneficiary",
        "Matching Right", "Competitive Restriction Exception",
    ]

    training_data = []
    seen = set()

    for row in ds:
        context = row.get("context", "")
        if not context or len(context) < 50:
            continue

        # Find which labels have answers
        for i, label in enumerate(CUAD_LABELS):
            answer_key = f"answer_{i}" if f"answer_{i}" in row else None
            answers = row.get("answers", {})

            if isinstance(answers, dict):
                texts = answers.get("text", [])
                if texts and texts[0]:
                    answer_text = texts[0]
                    dedup_key = f"{label}:{answer_text[:50]}"
                    if dedup_key in seen:
                        continue
                    seen.add(dedup_key)

                    training_data.append({
                        "instruction": f"Extract the {label} clause from this contract excerpt. Return the exact text.",
                        "input": context[:2000],
                        "output": answer_text
                    })

                    if len(training_data) >= max_examples:
                        return training_data

    return training_data


def generate_maud_training_data(max_examples=100):
    """
    Load MAUD dataset from HuggingFace and generate M&A clause analysis
    training examples. Run this on Kaggle.

    MAUD covers merger agreement clauses based on ABA model agreements.
    """
    from datasets import load_dataset
    import json

    try:
        ds = load_dataset("theatticusproject/maud", split="train")
    except Exception:
        return []

    training_data = []
    seen = set()

    for row in ds:
        question = row.get("question", "")
        context = row.get("context", row.get("text", ""))
        answer = row.get("answer", row.get("label", ""))

        if not question or not context:
            continue

        dedup_key = f"{question[:40]}:{str(answer)[:40]}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        training_data.append({
            "instruction": f"Analyze this merger agreement clause: {question}",
            "input": str(context)[:2000],
            "output": json.dumps({"question": question, "answer": str(answer), "source": "MAUD/ABA Model Merger Agreement"})
        })

        if len(training_data) >= max_examples:
            break

    return training_data


# Kaggle notebook cell code (copy-paste into notebook)
KAGGLE_CELL_CODE = '''
# Cell: Load CUAD + MAUD datasets and add to training data
# (Run this AFTER Cell 2 which generates base training data from LexAra clauses)

import sys
sys.path.insert(0, '/kaggle/working/lexara-api')

from app.services.reference_data.training_cuad_maud import (
    generate_cuad_training_data,
    generate_maud_training_data,
)
from app.services.reference_data.training_scenarios import SCENARIO_TRAINING_DATA
from app.services.reference_data.training_clause_pairs import (
    CLAUSE_PAIR_TRAINING_DATA,
    METADATA_EXTRACTION_TRAINING_DATA,
    PROCUREMENT_PROCESS_TRAINING_DATA,
)

# Add scenario-based reasoning chains
for scenario in SCENARIO_TRAINING_DATA:
    training_data.append({
        "instruction": scenario["instruction"],
        "input": scenario["context"],
        "output": scenario["response"],
    })
print(f"+ {len(SCENARIO_TRAINING_DATA)} scenario reasoning chains")

# Add clause-pairing (vendor vs customer-friendly)
for pair in CLAUSE_PAIR_TRAINING_DATA:
    training_data.append(pair)
print(f"+ {len(CLAUSE_PAIR_TRAINING_DATA)} clause pair comparisons")

# Add metadata extraction
for meta in METADATA_EXTRACTION_TRAINING_DATA:
    training_data.append(meta)
print(f"+ {len(METADATA_EXTRACTION_TRAINING_DATA)} metadata extraction examples")

# Add procurement process
for proc in PROCUREMENT_PROCESS_TRAINING_DATA:
    training_data.append(proc)
print(f"+ {len(PROCUREMENT_PROCESS_TRAINING_DATA)} procurement process examples")

# Add CUAD (real contract clause extraction)
try:
    cuad_data = generate_cuad_training_data(max_examples=200)
    training_data.extend(cuad_data)
    print(f"+ {len(cuad_data)} CUAD contract clause examples")
except Exception as e:
    print(f"CUAD loading skipped: {e}")

# Add MAUD (merger agreement analysis)
try:
    maud_data = generate_maud_training_data(max_examples=100)
    training_data.extend(maud_data)
    print(f"+ {len(maud_data)} MAUD merger agreement examples")
except Exception as e:
    print(f"MAUD loading skipped: {e}")

print(f"\\nTotal training examples: {len(training_data)}")
'''
