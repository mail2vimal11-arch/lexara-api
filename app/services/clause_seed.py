"""
Ontario-focused canonical clause seed data.
Run once at startup to populate the clause library with curated standard clauses.
"""

from sqlalchemy.orm import Session
from app.models.clause import SOWClause
from app.nlp.search import add_clause_to_index
import uuid

SEED_CLAUSES = [
    {
        "source": "Ontario",
        "clause_type": "Deliverables",
        "subtype": "Tangible_Deliverables",
        "clause_text": "The Contractor shall deliver all services and outputs in accordance with the specifications set out in this Scope of Work, including but not limited to reports, documentation, and system implementations, within the timelines specified in Schedule A.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Timeline_Milestones",
        "subtype": "Deadlines",
        "clause_text": "All deliverables must be completed within the timelines specified in Schedule A, and no later than 30 calendar days from the commencement date, unless otherwise approved in writing by Canada.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Performance_Standards",
        "subtype": "SLAs",
        "clause_text": "The Contractor shall meet the performance standards set out in Schedule B, including a minimum service availability of 99.5% measured on a monthly basis, and a maximum response time of four (4) hours for critical incidents.",
        "jurisdiction": "CA-ON",
        "industry": "IT",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Compliance_Regulatory",
        "subtype": "Accessibility",
        "clause_text": "All deliverables, systems, and digital content provided under this Contract must comply with the Accessibility for Ontarians with Disabilities Act, 2005, SO 2005, c 11 (AODA), including the Integrated Accessibility Standards Regulation, O Reg 191/11.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Compliance_Regulatory",
        "subtype": "Data_Protection",
        "clause_text": "The Contractor shall comply with the Personal Information Protection and Electronic Documents Act, SC 2000, c 5, and the Freedom of Information and Protection of Privacy Act, RSO 1990, c F-31, in its collection, use, and disclosure of personal information under this Contract.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Commercial_Terms",
        "subtype": "Payment_Milestones",
        "clause_text": "Payment shall be made upon successful completion and written acceptance of each milestone as defined in Schedule A. Canada shall pay undisputed invoices within thirty (30) calendar days of receipt. Late payments shall accrue interest pursuant to the Interest and Administrative Charges Regulations, SOR/96-188.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Risk_Allocation",
        "subtype": "Indemnity_Linked_Scope",
        "clause_text": "The Contractor shall indemnify and hold harmless Canada, its officers, employees, and agents from and against any and all claims, damages, losses, costs, and expenses arising out of or related to: (a) any breach by the Contractor of this Contract; (b) any negligent or wrongful act or omission of the Contractor; or (c) any infringement of intellectual property rights by the Contractor.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Termination",
        "subtype": "Termination_Convenience",
        "clause_text": "Canada may, at any time, terminate this Contract for convenience by providing thirty (30) calendar days' written notice to the Contractor. Upon termination for convenience, Canada's liability is limited to payment for work satisfactorily performed and accepted prior to the termination date, together with reasonable and substantiated wind-down costs.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Change_Management",
        "subtype": "Change_Request_Process",
        "clause_text": "Any change to the scope of work set out in this Contract must be requested in writing and approved by both parties prior to implementation. The Contractor shall provide a written impact assessment, including any changes to cost, timeline, or deliverables, within five (5) business days of receiving a change request.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Acceptance_Closure",
        "subtype": "Acceptance_Criteria",
        "clause_text": "Canada shall have fifteen (15) business days following receipt of each deliverable to review and either: (a) provide written acceptance; or (b) provide written notice of non-conformance specifying the deficiencies in reasonable detail. The Contractor shall cure all identified deficiencies within ten (10) business days. Failure to respond within the review period shall constitute deemed acceptance.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Intellectual_Property",
        "subtype": "Crown_Ownership",
        "clause_text": "All intellectual property created, developed, or first reduced to practice by the Contractor in the performance of this Contract shall vest in and be owned exclusively by Canada upon creation. The Contractor hereby assigns to Canada all right, title, and interest in such intellectual property and agrees to execute any further instruments required to perfect such assignment.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
    {
        "source": "Ontario",
        "clause_type": "Confidentiality",
        "subtype": "Non_Disclosure",
        "clause_text": "The Contractor agrees to hold in strict confidence all Confidential Information of Canada and shall not disclose such information to any third party without prior written consent. The Contractor shall use Confidential Information solely for the purpose of performing its obligations under this Contract.",
        "jurisdiction": "CA-ON",
        "industry": "General",
        "risk_level": "Low",
        "is_standard": True,
    },
]


def seed_clauses(db: Session) -> int:
    """
    Insert seed clauses if not already present. Returns count of clauses inserted.
    Only runs once — skips if standard clauses already exist in the DB.
    """
    existing = db.query(SOWClause).filter(SOWClause.is_standard == True).count()  # noqa
    if existing >= len(SEED_CLAUSES):
        return 0

    inserted = 0
    for data in SEED_CLAUSES:
        clause_id = str(uuid.uuid4())
        clause = SOWClause(clause_id=clause_id, confidence_score=1.0, **data)
        db.add(clause)
        add_clause_to_index(clause_id, data["clause_text"], data["clause_type"])
        inserted += 1

    db.commit()
    return inserted
