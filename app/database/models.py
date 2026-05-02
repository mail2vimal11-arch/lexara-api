"""Legacy models module — superseded by app/models/.

All models have been moved:
- User        → app/models/user.py     (CA-002: merged auth + billing columns)
- APIKey      → app/models/billing.py  (CA-018)
- Analysis    → app/models/billing.py  (CA-018, CA-001: timedelta import fixed)
- UsageLog    → app/models/billing.py  (CA-018)
- BillingEvent→ app/models/billing.py  (CA-018)

This file is intentionally empty to avoid the duplicate-mapper collision
that caused the original CA-002 bug. Do not re-add models here.
"""
