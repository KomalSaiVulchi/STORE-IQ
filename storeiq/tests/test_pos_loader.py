"""Unit tests for the POS transaction loader."""
# PROMPT: Create tests for pos_loader.py to verify CSV parsing and timestamp conversion.
# CHANGES MADE: New test file covering timestamp timezone conversion and deduplication.

import os
import tempfile
from datetime import datetime, timezone, timedelta

from pipeline.pos_loader import parse_brigade_csv, _parse_timestamp


def test_parse_timestamp():
    """Test date/time parsing into UTC."""
    # IST to UTC conversion test
    # 10-04-2026 14:30:00 IST -> 10-04-2026 09:00:00 UTC
    dt = _parse_timestamp("10-04-2026", "14:30:00")
    assert dt is not None
    assert dt.tzinfo == timezone.utc
    assert dt.hour == 9
    assert dt.minute == 0
    
    # Missing time
    dt = _parse_timestamp("10-04-2026", "")
    assert dt is not None
    assert dt.hour == 18 # 00:00 IST -> 18:30 UTC previous day
    assert dt.minute == 30
    
    # Invalid date
    dt = _parse_timestamp("invalid", "invalid")
    assert dt is None


def test_parse_brigade_csv():
    """Test parsing CSV with deduplication."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("order_id,order_date,order_time,total_amount,invoice_number,customer_name\n")
        f.write("101,10-04-2026,14:30:00,1500.50,INV-001,John Doe\n")
        # Duplicate order_id, should be skipped
        f.write("101,10-04-2026,14:30:00,500.00,INV-001,John Doe\n")
        # Different order_id
        f.write("102,10-04-2026,15:45:00,2000.00,INV-002,Jane Doe\n")
        
    try:
        transactions = parse_brigade_csv(f.name)
        assert len(transactions) == 2
        
        assert transactions[0]["transaction_id"] == "TXN_101"
        assert transactions[0]["basket_value_inr"] == 1500.50
        assert transactions[0]["store_id"] == "STORE_BLR_002"
        
        assert transactions[1]["transaction_id"] == "TXN_102"
        assert transactions[1]["basket_value_inr"] == 2000.00
        
    finally:
        os.unlink(f.name)
