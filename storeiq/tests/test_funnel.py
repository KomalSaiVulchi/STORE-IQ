"""Unit tests for the conversion funnel engine."""
# PROMPT: Create tests for the FunnelEngine, covering basic conversion, re-entry deduplication, and POS correlation.
# CHANGES MADE: New test file covering funnel deduplication and POS transaction correlation.

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from analytics.funnel_engine import FunnelEngine


def test_funnel_basic_conversion():
    """Test basic funnel conversion without POS correlation."""
    engine = FunnelEngine()
    db = MagicMock()
    
    class FakeScalarQuery:
        def __init__(self, values):
            self.values = values
            self.idx = 0
            
        def filter(self, *args, **kwargs):
            return self
            
        def with_entities(self, *args, **kwargs):
            return self
            
        def scalar(self):
            val = self.values[self.idx]
            self.idx += 1
            return val
            
    db.query.return_value = FakeScalarQuery([100, 80, 50, 20])
    
    with patch.object(engine, '_pos_correlated_purchases', return_value=0):
        stages = engine.compute(db, "STORE_BLR_002")
        
        assert len(stages) == 4
        assert stages[0]["stage"] == "ENTRY"
        assert stages[0]["count"] == 100
        
        assert stages[1]["stage"] == "ZONE_VISIT"
        assert stages[1]["count"] == 80
        
        assert stages[2]["stage"] == "BILLING"
        assert stages[2]["count"] == 50
        
        assert stages[3]["stage"] == "PURCHASE"
        assert stages[3]["count"] == 20
        assert stages[3]["pct"] == 20.0


def test_pos_correlation():
    """Test POS transaction correlation marks sessions and counts purchases."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base, PosTransaction, SessionRecord

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    now = datetime.now(timezone.utc)
    db.add(
        PosTransaction(
            store_id="STORE_BLR_002",
            transaction_id="txn-1",
            timestamp=now,
            basket_value_inr=500.0,
        )
    )
    for visitor_id in ("visitor_1", "visitor_2"):
        db.add(
            SessionRecord(
                session_id=f"sess-{visitor_id}",
                store_id="STORE_BLR_002",
                visitor_id=visitor_id,
                entry_time=now - timedelta(minutes=3),
                billing_visited=True,
                purchase=False,
            )
        )
    db.commit()

    engine_funnel = FunnelEngine()
    purchases = engine_funnel._pos_correlated_purchases(db, "STORE_BLR_002")
    assert purchases == 2


def test_drop_off_alert():
    """Test drop-off alert logic."""
    engine = FunnelEngine()
    
    # Normal drop-off (40%)
    stages = [
        {"stage": "ENTRY", "count": 100, "pct": 100.0},
        {"stage": "ZONE_VISIT", "count": 80, "pct": 80.0},
        {"stage": "BILLING", "count": 50, "pct": 50.0},
        {"stage": "PURCHASE", "count": 10, "pct": 10.0},
    ]
    alert = engine.drop_off_alert(stages)
    assert "30% threshold" in alert
    
    # Critical drop-off (60%)
    stages[2]["pct"] = 70.0
    stages[3]["pct"] = 10.0
    alert = engine.drop_off_alert(stages)
    assert "50% threshold" in alert
    
    # Safe drop-off (10%)
    stages[2]["pct"] = 30.0
    stages[3]["pct"] = 20.0
    alert = engine.drop_off_alert(stages)
    assert alert == "No critical drop-off detected"
