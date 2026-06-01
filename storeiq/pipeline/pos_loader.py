"""POS transaction loader — parses Brigade CSV into database."""

from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.config import get_settings
from database.models import Base, PosTransaction

logger = logging.getLogger("storeiq-pipeline")

# Default store mapping for the Brigade Bangalore store
STORE_ID = "STORE_BLR_002"


def parse_brigade_csv(csv_path: str) -> list[dict]:
    """Parse the Brigade Bangalore POS CSV and return transaction records.

    Maps CSV columns to POS schema:
    - store_id: derived from store_name → STORE_BLR_002
    - transaction_id: order_id
    - timestamp: order_date + order_time → ISO-8601
    - basket_value_inr: total_amount
    - invoice_number: invoice_number
    - customer_name: customer_name
    """
    transactions = []
    seen_orders = set()

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            order_id = row.get("order_id", "").strip()
            if not order_id:
                continue

            # Deduplicate by order_id (each order may have multiple line items)
            if order_id in seen_orders:
                continue
            seen_orders.add(order_id)

            # Parse date and time
            order_date = row.get("order_date", "").strip()
            order_time = row.get("order_time", "").strip()
            timestamp = _parse_timestamp(order_date, order_time)
            if not timestamp:
                continue

            # Parse total amount
            try:
                total_amount = float(row.get("total_amount", "0").strip() or "0")
            except ValueError:
                total_amount = 0.0

            transactions.append({
                "store_id": STORE_ID,
                "transaction_id": f"TXN_{order_id}",
                "timestamp": timestamp,
                "basket_value_inr": total_amount,
                "invoice_number": row.get("invoice_number", "").strip(),
                "customer_name": row.get("customer_name", "").strip(),
            })

    return transactions


def _parse_timestamp(date_str: str, time_str: str) -> Optional[datetime]:
    """Parse date (DD-MM-YYYY) + time (HH:MM:SS) into UTC datetime."""
    if not date_str:
        return None
    try:
        # Date format: DD-MM-YYYY
        dt = datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")
        # Assume IST (UTC+5:30), convert to UTC
        from datetime import timedelta
        ist_offset = timedelta(hours=5, minutes=30)
        utc_dt = dt - ist_offset
        return utc_dt.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            dt = datetime.strptime(date_str, "%d-%m-%Y")
            from datetime import timedelta
            ist_offset = timedelta(hours=5, minutes=30)
            utc_dt = dt - ist_offset
            return utc_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def load_pos_transactions(csv_path: str, database_url: Optional[str] = None) -> int:
    """Load POS transactions from CSV into the database.

    Returns the number of transactions loaded.
    """
    if database_url is None:
        settings = get_settings()
        database_url = settings.database_url

    engine = create_engine(database_url, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    transactions = parse_brigade_csv(csv_path)
    loaded = 0

    with session_local() as db:
        for txn in transactions:
            existing = (
                db.query(PosTransaction)
                .filter(PosTransaction.transaction_id == txn["transaction_id"])
                .one_or_none()
            )
            if existing:
                continue

            record = PosTransaction(
                store_id=txn["store_id"],
                transaction_id=txn["transaction_id"],
                timestamp=txn["timestamp"],
                basket_value_inr=txn["basket_value_inr"],
                invoice_number=txn["invoice_number"],
                customer_name=txn["customer_name"],
            )
            db.add(record)
            loaded += 1

        db.commit()

    logger.info({"message": "POS transactions loaded", "count": loaded, "source": csv_path})
    return loaded


if __name__ == "__main__":
    import sys

    default_csv = Path(__file__).resolve().parent.parent / "dataset" / "Brigade_Bangalore_10_April_26 (1)bc6219c.csv"
    csv_file = sys.argv[1] if len(sys.argv) > 1 else str(default_csv)
    count = load_pos_transactions(csv_file)
    print(f"Loaded {count} POS transactions from {csv_file}")
