"""Reference data package — split clause library by category."""
from app.services.reference_data.core_clauses import CORE_CLAUSES
from app.services.reference_data.procurement_clauses import PROCUREMENT_CLAUSES
from app.services.reference_data.financial_clauses import FINANCIAL_CLAUSES
from app.services.reference_data.scope_clauses import SCOPE_CLAUSES
from app.services.reference_data.risk_clauses import RISK_CLAUSES
from app.services.reference_data.ip_data_clauses import IP_DATA_CLAUSES
from app.services.reference_data.compliance_clauses import COMPLIANCE_CLAUSES
from app.services.reference_data.termination_clauses import TERMINATION_CLAUSES
from app.services.reference_data.sector_clauses import SECTOR_CLAUSES
from app.services.reference_data.international_clauses import INTERNATIONAL_CLAUSES

ALL_REFERENCE_CLAUSES = (
    CORE_CLAUSES
    + PROCUREMENT_CLAUSES
    + FINANCIAL_CLAUSES
    + SCOPE_CLAUSES
    + RISK_CLAUSES
    + IP_DATA_CLAUSES
    + COMPLIANCE_CLAUSES
    + TERMINATION_CLAUSES
    + SECTOR_CLAUSES
    + INTERNATIONAL_CLAUSES
)
