"""
Knowledge DB seeder for the SOW Workbench (Feature 2).

Populates jurisdictions, procurement frameworks, commodity taxonomy, and
knowledge articles from the seed-data modules under app/data/. Each
seeder is idempotent: safe to call on every startup.

Public entry points:
    seed_all_knowledge(db)        -> dict of insert counts (called from main.py)
    seed_jurisdictions(db)        -> int
    seed_procurement_frameworks(db) -> int
    seed_commodity_taxonomy(db)   -> dict of (sectors, categories, subcategories)
    seed_knowledge_articles(db)   -> int
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.data.jurisdictions_data import JURISDICTIONS, PROCUREMENT_FRAMEWORKS
from app.data.commodity_taxonomy_seed import COMMODITY_TAXONOMY
from app.data.knowledge_articles_seed import KNOWLEDGE_ARTICLES
from app.models.jurisdiction import Jurisdiction
from app.models.commodity import (
    CommoditySector,
    CommodityCategory,
    CommoditySubcategory,
)
from app.models.knowledge import ProcurementFramework, KnowledgeArticle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Jurisdictions
# ---------------------------------------------------------------------------

def seed_jurisdictions(db: Session) -> int:
    """Insert any jurisdictions in JURISDICTIONS that are not yet in the DB."""
    existing = {j.code for j in db.query(Jurisdiction.code).all()}
    inserted = 0
    for row in JURISDICTIONS:
        if row["code"] in existing:
            continue
        db.add(Jurisdiction(**row))
        inserted += 1
    if inserted:
        db.commit()
    return inserted


# ---------------------------------------------------------------------------
# Procurement frameworks
# ---------------------------------------------------------------------------

def seed_procurement_frameworks(db: Session) -> int:
    """
    Insert any procurement frameworks in PROCUREMENT_FRAMEWORKS that don't
    yet exist. Uniqueness key: (jurisdiction_id, framework_name).
    """
    juris_by_code = {j.code: j for j in db.query(Jurisdiction).all()}

    existing_keys = {
        (fw.jurisdiction_id, fw.framework_name)
        for fw in db.query(ProcurementFramework.jurisdiction_id, ProcurementFramework.framework_name).all()
    }

    inserted = 0
    for row in PROCUREMENT_FRAMEWORKS:
        jur = juris_by_code.get(row["jurisdiction_code"])
        if jur is None:
            logger.warning(
                "seed_procurement_frameworks: skipping unknown jurisdiction %r",
                row["jurisdiction_code"],
            )
            continue

        if (jur.id, row["framework_name"]) in existing_keys:
            continue

        # Strip keys that don't map to columns + handle effective_date
        data = {k: v for k, v in row.items() if k != "jurisdiction_code"}

        # The model has columns for ceta/cusma/cfta construction thresholds —
        # but the seed dicts include cusma_construction_threshold and
        # ceta_construction_threshold which are not on the model. Drop them.
        data.pop("cusma_construction_threshold", None)
        data.pop("ceta_construction_threshold", None)

        eff_raw = data.get("effective_date")
        if isinstance(eff_raw, str):
            try:
                data["effective_date"] = date.fromisoformat(eff_raw)
            except ValueError:
                data["effective_date"] = None

        db.add(ProcurementFramework(jurisdiction_id=jur.id, **data))
        inserted += 1

    if inserted:
        db.commit()
    return inserted


# ---------------------------------------------------------------------------
# Commodity taxonomy
# ---------------------------------------------------------------------------

def seed_commodity_taxonomy(db: Session) -> dict:
    """
    Insert commodity sectors, categories, and subcategories that don't yet
    exist. Uniqueness keys: code (for each level).
    Returns: {"sectors": n, "categories": n, "subcategories": n}
    """
    counts = {"sectors": 0, "categories": 0, "subcategories": 0}

    sectors_by_code = {s.code: s for s in db.query(CommoditySector).all()}
    categories_by_code = {c.code: c for c in db.query(CommodityCategory).all()}
    subcategories_by_code = {sc.code: sc for sc in db.query(CommoditySubcategory).all()}

    for sector_data in COMMODITY_TAXONOMY:
        sector = sectors_by_code.get(sector_data["code"])
        if sector is None:
            sector = CommoditySector(
                code=sector_data["code"],
                name=sector_data["name"],
                name_fr=sector_data.get("name_fr"),
                description=sector_data.get("description"),
                ui_icon=sector_data.get("ui_icon"),
                display_order=sector_data.get("display_order", 0),
            )
            db.add(sector)
            db.flush()  # populate sector.id
            sectors_by_code[sector.code] = sector
            counts["sectors"] += 1

        for cat_data in sector_data.get("categories", []):
            category = categories_by_code.get(cat_data["code"])
            if category is None:
                category = CommodityCategory(
                    sector_id=sector.id,
                    code=cat_data["code"],
                    name=cat_data["name"],
                    name_fr=cat_data.get("name_fr"),
                    description=cat_data.get("description"),
                    typical_contract_types=cat_data.get("typical_contract_types"),
                    typical_duration_months=cat_data.get("typical_duration_months"),
                    value_range_min_cad=cat_data.get("value_range_min_cad"),
                    value_range_max_cad=cat_data.get("value_range_max_cad"),
                    cpv_codes=cat_data.get("cpv_codes"),
                    unspsc_codes=cat_data.get("unspsc_codes"),
                    key_considerations=cat_data.get("key_considerations"),
                    display_order=cat_data.get("display_order", 0),
                )
                db.add(category)
                db.flush()
                categories_by_code[category.code] = category
                counts["categories"] += 1

            for sub_data in cat_data.get("subcategories", []):
                if sub_data["code"] in subcategories_by_code:
                    continue
                subcategory = CommoditySubcategory(
                    category_id=category.id,
                    code=sub_data["code"],
                    name=sub_data["name"],
                    name_fr=sub_data.get("name_fr"),
                    description=sub_data.get("description"),
                    special_requirements=sub_data.get("special_requirements"),
                    typical_deliverables=sub_data.get("typical_deliverables"),
                    typical_evaluation_criteria=sub_data.get("typical_evaluation_criteria"),
                )
                db.add(subcategory)
                subcategories_by_code[subcategory.code] = subcategory
                counts["subcategories"] += 1

    if any(counts.values()):
        db.commit()
    return counts


# ---------------------------------------------------------------------------
# Knowledge articles
# ---------------------------------------------------------------------------

def _resolve_optional_id(
    code: Optional[str],
    lookup: dict,
    article_id: str,
    label: str,
) -> Optional[int]:
    if not code:
        return None
    obj = lookup.get(code)
    if obj is None:
        logger.warning(
            "seed_knowledge_articles: %s — unknown %s code %r, falling back to NULL",
            article_id, label, code,
        )
        return None
    return obj.id


def seed_knowledge_articles(db: Session) -> int:
    """
    Insert knowledge articles. Uniqueness key: article_id.
    Translates string scope codes (jurisdiction_code, commodity_category_code,
    commodity_subcategory_code) into FK integer IDs.
    """
    juris_by_code = {j.code: j for j in db.query(Jurisdiction).all()}
    cat_by_code = {c.code: c for c in db.query(CommodityCategory).all()}
    sub_by_code = {sc.code: sc for sc in db.query(CommoditySubcategory).all()}
    existing_ids = {a.article_id for a in db.query(KnowledgeArticle.article_id).all()}

    inserted = 0
    now = datetime.utcnow()

    for row in KNOWLEDGE_ARTICLES:
        if row["article_id"] in existing_ids:
            continue

        jur_id = _resolve_optional_id(
            row.get("jurisdiction_code"), juris_by_code, row["article_id"], "jurisdiction"
        )
        cat_id = _resolve_optional_id(
            row.get("commodity_category_code"), cat_by_code, row["article_id"], "commodity_category"
        )
        sub_id = _resolve_optional_id(
            row.get("commodity_subcategory_code"), sub_by_code, row["article_id"], "commodity_subcategory"
        )

        article = KnowledgeArticle(
            article_id=row["article_id"],
            jurisdiction_id=jur_id,
            commodity_category_id=cat_id,
            commodity_subcategory_id=sub_id,
            article_type=row["article_type"],
            procurement_phase=row["procurement_phase"],
            section_type=row["section_type"],
            title=row["title"],
            title_fr=row.get("title_fr"),
            content=row["content"],
            content_fr=row.get("content_fr"),
            template_text=row.get("template_text"),
            template_text_fr=row.get("template_text_fr"),
            guidance_note=row.get("guidance_note"),
            source=row.get("source"),
            source_ref=row.get("source_ref"),
            source_url=row.get("source_url"),
            is_mandatory=bool(row.get("is_mandatory", False)),
            importance=row.get("importance", "medium"),
            risk_if_omitted=row.get("risk_if_omitted"),
            applies_above_value_cad=row.get("applies_above_value_cad"),
            applies_to_methods=row.get("applies_to_methods"),
            tags=row.get("tags"),
            related_article_ids=row.get("related_article_ids"),
            version=row.get("version", "1.0"),
            is_active=bool(row.get("is_active", True)),
            created_at=now,
            updated_at=now,
        )
        db.add(article)
        inserted += 1

    if inserted:
        db.commit()
    return inserted


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def seed_all_knowledge(db: Session) -> dict:
    """
    Run every Workbench seeder in dependency order.

    Returns insert counts per stage. Empty values mean no new rows were
    needed (typical for warm starts).
    """
    results = {
        "jurisdictions": seed_jurisdictions(db),
        "procurement_frameworks": seed_procurement_frameworks(db),
    }
    taxonomy = seed_commodity_taxonomy(db)
    results.update({
        "commodity_sectors": taxonomy["sectors"],
        "commodity_categories": taxonomy["categories"],
        "commodity_subcategories": taxonomy["subcategories"],
    })
    results["knowledge_articles"] = seed_knowledge_articles(db)
    return results
