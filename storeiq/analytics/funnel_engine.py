"""Conversion funnel analytics with POS transaction correlation."""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.event_processor import mark_pos_purchases
from database.models import PosTransaction, SessionRecord


class FunnelEngine:
    """Compute funnel stage counts and drop-off alerts.

    Purchase stage uses POS correlation: visitor in billing zone within
  5 minutes before transaction timestamp (per problem statement).
    """

    def compute(self, db: Session, store_id: Optional[str] = None) -> List[Dict[str, float]]:
        base_query = db.query(SessionRecord)
        if store_id:
            base_query = base_query.filter(SessionRecord.store_id == store_id)

        total = (
            base_query.with_entities(func.count(func.distinct(SessionRecord.visitor_id))).scalar() or 0
        )

        zone_visit = (
            base_query.filter(SessionRecord.zones_visited.isnot(None))
            .with_entities(func.count(func.distinct(SessionRecord.visitor_id)))
            .scalar()
            or 0
        )

        billing = (
            base_query.filter(SessionRecord.billing_visited.is_(True))
            .with_entities(func.count(func.distinct(SessionRecord.visitor_id)))
            .scalar()
            or 0
        )

        purchase = self._pos_correlated_purchases(db, store_id)
        if purchase == 0:
            purchase = (
                base_query.filter(SessionRecord.purchase.is_(True))
                .with_entities(func.count(func.distinct(SessionRecord.visitor_id)))
                .scalar()
                or 0
            )

        return [
            self._stage("ENTRY", total, total),
            self._stage("ZONE_VISIT", zone_visit, total),
            self._stage("BILLING", billing, total),
            self._stage("PURCHASE", purchase, total),
        ]

    def _pos_correlated_purchases(self, db: Session, store_id: Optional[str]) -> int:
        """Count unique visitors with billing overlap in the 5-minute pre-transaction window."""
        try:
            mark_pos_purchases(db, store_id)
            query = db.query(SessionRecord).filter(SessionRecord.purchase.is_(True))
            if store_id:
                query = query.filter(SessionRecord.store_id == store_id)
            return query.with_entities(func.count(func.distinct(SessionRecord.visitor_id))).scalar() or 0
        except Exception:
            db.rollback()
            return 0

    def drop_off_alert(self, stages: List[Dict[str, float]]) -> str:
        billing = stages[2]["pct"] if len(stages) > 2 else 0
        purchase = stages[3]["pct"] if len(stages) > 3 else 0
        drop = round(billing - purchase, 1)
        if drop > 50:
            return f"BILLING→PURCHASE drop-off is {drop}% — above 50% threshold"
        if drop > 30:
            return f"BILLING→PURCHASE drop-off is {drop}% — above 30% threshold"
        return "No critical drop-off detected"

    @staticmethod
    def _stage(name: str, count: int, total: int) -> Dict[str, float]:
        pct = round((count / total * 100), 1) if total else 0.0
        return {"stage": name, "count": count, "pct": pct}
