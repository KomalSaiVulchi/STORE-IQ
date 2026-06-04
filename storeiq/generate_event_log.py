"""Generate event_log.jsonl matching the exact sample_events.jsonl schema.

This script simulates realistic visitor journeys through the Brigade Bangalore
store on 2026-04-10 (matching POS transaction data) and outputs events in the
exact JSONL schema required by the submission guidelines.

Event types:
  - entry / exit          (cam1 — entry/exit camera)
  - zone_entered / zone_exited (cam2–cam5 — floor cameras)
  - queue_completed / queue_abandoned (billing camera)
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path


# ── Store Configuration ──────────────────────────────────────────────────────

STORE_CODE = "STORE_BLR_002"       # entry/exit events
STORE_ID   = "STORE_BLR_002"       # zone / queue events
BASE_DATE  = datetime(2026, 4, 10, 10, 0, 0)  # store opens 10:00
CLOSE_HOUR = 22                                 # store closes 22:00

# Camera mapping
CAM_ENTRY   = "CAM_ENTRY_01"
CAM_FLOOR   = "CAM_FLOOR_02"
CAM_BILLING = "CAM_BILLING_03"
CAM_SKIN    = "CAM_SKINCARE_04"
CAM_MAKEUP  = "CAM_MAKEUP_05"

# Zone definitions: (zone_id, zone_name, zone_type, is_revenue_zone, camera_id)
ZONES = [
    ("SKINCARE",      "Skincare Section",      "SHELF",   "Yes", CAM_SKIN),
    ("MAKEUP",        "Makeup Section",        "SHELF",   "Yes", CAM_MAKEUP),
    ("HAIRCARE",      "Haircare Section",      "SHELF",   "Yes", CAM_FLOOR),
    ("FRAGRANCE",     "Fragrance Display",     "DISPLAY", "Yes", CAM_SKIN),
    ("PERSONAL_CARE", "Personal Care Section", "SHELF",   "Yes", CAM_MAKEUP),
]

BILLING_ZONE = {
    "zone_id":   "BILLING",
    "zone_name": "Billing Counter",
    "zone_type": "BILLING",
    "is_revenue_zone": "Yes",
    "camera_id": CAM_BILLING,
}

# Demographics distributions
GENDERS   = ["M", "F"]
AGE_BUCKETS = {
    "18-24": (18, 24),
    "25-34": (25, 34),
    "35-44": (35, 44),
    "45-54": (45, 54),
    "55+":   (55, 65),
}
AGE_BUCKET_WEIGHTS = [0.20, 0.35, 0.25, 0.12, 0.08]

# ── Helpers ──────────────────────────────────────────────────────────────────

def ts_str(dt: datetime) -> str:
    """ISO timestamp with microseconds, no timezone."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def random_hotspot(zone_id: str) -> tuple[float, float]:
    """Return a plausible (x, y) pixel coordinate for a zone."""
    zone_centers = {
        "SKINCARE":      (380, 320),
        "MAKEUP":        (520, 280),
        "HAIRCARE":      (650, 410),
        "FRAGRANCE":     (440, 370),
        "PERSONAL_CARE": (560, 350),
        "BILLING":       (610, 190),
        "ENTRANCE":      (400, 500),
    }
    cx, cy = zone_centers.get(zone_id, (400, 300))
    return round(cx + random.uniform(-40, 40), 1), round(cy + random.uniform(-40, 40), 1)


def pick_age_bucket() -> tuple[str, int]:
    """Return (age_bucket, age) tuple."""
    bucket = random.choices(list(AGE_BUCKETS.keys()), weights=AGE_BUCKET_WEIGHTS, k=1)[0]
    lo, hi = AGE_BUCKETS[bucket]
    return bucket, random.randint(lo, hi)


# ── Event Builders ───────────────────────────────────────────────────────────

def make_entry_event(id_token: str, ts: datetime, is_staff: bool,
                     gender: str, age: int, age_bucket: str,
                     group_id: str | None, group_size: int | None,
                     is_face_hidden: bool = False) -> dict:
    return {
        "event_type": "entry",
        "id_token": id_token,
        "store_code": STORE_CODE,
        "camera_id": CAM_ENTRY,
        "event_timestamp": ts_str(ts),
        "is_staff": is_staff,
        "gender_pred": gender,
        "age_pred": age,
        "age_bucket": age_bucket,
        "is_face_hidden": is_face_hidden,
        "group_id": group_id,
        "group_size": group_size,
    }


def make_exit_event(id_token: str, ts: datetime, is_staff: bool,
                    gender: str, age: int, age_bucket: str,
                    group_id: str | None, group_size: int | None,
                    is_face_hidden: bool = False) -> dict:
    return {
        "event_type": "exit",
        "id_token": id_token,
        "store_code": STORE_CODE,
        "camera_id": CAM_ENTRY,
        "event_timestamp": ts_str(ts),
        "is_staff": is_staff,
        "gender_pred": gender,
        "age_pred": age,
        "age_bucket": age_bucket,
        "is_face_hidden": is_face_hidden,
        "group_id": group_id,
        "group_size": group_size,
    }


def make_zone_entered(track_id: int, zone: tuple, ts: datetime,
                      gender: str, age: int, age_bucket: str) -> dict:
    zone_id, zone_name, zone_type, is_rev, cam_id = zone
    hx, hy = random_hotspot(zone_id)
    return {
        "event_type": "zone_entered",
        "track_id": track_id,
        "store_id": STORE_ID,
        "camera_id": cam_id,
        "zone_id": f"PURPLLE_BLR_002_{zone_id}",
        "zone_name": zone_name,
        "zone_type": zone_type,
        "is_revenue_zone": is_rev,
        "event_time": ts_str(ts),
        "zone_hotspot_x": hx,
        "zone_hotspot_y": hy,
        "gender": gender,
        "age": age,
        "age_bucket": age_bucket,
    }


def make_zone_exited(track_id: int, zone: tuple, ts: datetime,
                     gender: str, age: int, age_bucket: str) -> dict:
    zone_id, zone_name, zone_type, is_rev, cam_id = zone
    hx, hy = random_hotspot(zone_id)
    return {
        "event_type": "zone_exited",
        "track_id": track_id,
        "store_id": STORE_ID,
        "camera_id": cam_id,
        "zone_id": f"PURPLLE_BLR_002_{zone_id}",
        "zone_name": zone_name,
        "zone_type": zone_type,
        "is_revenue_zone": is_rev,
        "event_time": ts_str(ts),
        "zone_hotspot_x": hx,
        "zone_hotspot_y": hy,
        "gender": gender,
        "age": age,
        "age_bucket": age_bucket,
    }


def make_queue_event(track_id: int, join_ts: datetime, served_ts: datetime | None,
                     exit_ts: datetime, wait_sec: int, position: int,
                     abandoned: bool, gender: str, age: int, age_bucket: str) -> dict:
    bz = BILLING_ZONE
    hx, hy = random_hotspot("BILLING")
    return {
        "queue_event_id": str(uuid.uuid4()),
        "event_type": "queue_abandoned" if abandoned else "queue_completed",
        "track_id": track_id,
        "store_id": STORE_ID,
        "camera_id": bz["camera_id"],
        "zone_id": f"PURPLLE_BLR_002_BILLING_01",
        "zone_name": bz["zone_name"],
        "zone_type": bz["zone_type"],
        "is_revenue_zone": bz["is_revenue_zone"],
        "queue_join_ts": ts_str(join_ts),
        "queue_served_ts": ts_str(served_ts) if served_ts else None,
        "queue_exit_ts": ts_str(exit_ts),
        "wait_seconds": wait_sec,
        "queue_position_at_join": position,
        "abandoned": abandoned,
        "zone_hotspot_x": hx,
        "zone_hotspot_y": hy,
        "gender": gender,
        "age": age,
        "age_bucket": age_bucket,
    }


# ── Journey Simulation ──────────────────────────────────────────────────────

def simulate_day() -> list[dict]:
    """Simulate a full day of visitor journeys."""
    events: list[dict] = []
    random.seed(42)  # Reproducible

    # Hourly arrival rates (index 0 = 10:00, index 11 = 21:00)
    hourly_rates = [12, 15, 22, 25, 18, 14, 20, 28, 35, 30, 22, 10]

    visitor_counter = 0
    track_counter = 100
    group_counter = 0
    queue_position = 0
    staff_ids_emitted = set()

    # Generate 6 staff members who enter/exit throughout the day
    staff_schedule = [
        (10, 0, 18, 0),   # morning shift 1
        (10, 0, 18, 0),   # morning shift 2
        (10, 15, 18, 30),  # morning shift 3
        (14, 0, 22, 0),   # evening shift 1
        (14, 0, 22, 0),   # evening shift 2
        (14, 30, 22, 0),  # evening shift 3
    ]

    for i, (sh, sm, eh, em) in enumerate(staff_schedule):
        sid = f"STAFF_{i+1:03d}"
        gender = random.choice(GENDERS)
        age_bucket, age = pick_age_bucket()
        entry_ts = BASE_DATE.replace(hour=sh, minute=sm, second=random.randint(0, 59))
        exit_ts = BASE_DATE.replace(hour=eh, minute=em, second=random.randint(0, 59))

        events.append(make_entry_event(sid, entry_ts, True, gender, age, age_bucket, None, None))
        events.append(make_exit_event(sid, exit_ts, True, gender, age, age_bucket, None, None))

    # Generate visitor journeys
    for hour_offset, count in enumerate(hourly_rates):
        hour = 10 + hour_offset

        for _ in range(count):
            visitor_counter += 1
            track_counter += 1
            track_id = track_counter

            gender = random.choice(GENDERS)
            age_bucket, age = pick_age_bucket()
            is_face_hidden = random.random() < 0.08  # 8% faces hidden

            # Random arrival within the hour
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            microsecond = random.randint(0, 999999)
            entry_ts = BASE_DATE.replace(hour=hour, minute=minute, second=second,
                                         microsecond=microsecond)

            # Group handling: ~15% of visitors are in groups of 2-4
            group_id = None
            group_size = None
            extra_members = []
            if random.random() < 0.15:
                group_counter += 1
                group_id = f"G_{group_counter}"
                group_size = random.choice([2, 2, 2, 3, 4])  # weighted toward pairs
                for g in range(group_size - 1):
                    visitor_counter += 1
                    track_counter += 1
                    g_gender = random.choice(GENDERS)
                    g_age_bucket, g_age = pick_age_bucket()
                    g_entry_ts = entry_ts + timedelta(seconds=random.uniform(1, 5))
                    extra_members.append({
                        "id_token": f"ID_{visitor_counter:05d}",
                        "track_id": track_counter,
                        "gender": g_gender,
                        "age": g_age,
                        "age_bucket": g_age_bucket,
                        "entry_ts": g_entry_ts,
                        "is_face_hidden": random.random() < 0.08,
                    })

            id_token = f"ID_{visitor_counter:05d}"

            # ── ENTRY event ──
            events.append(make_entry_event(
                id_token, entry_ts, False, gender, age, age_bucket,
                group_id, group_size, is_face_hidden
            ))
            for gm in extra_members:
                events.append(make_entry_event(
                    gm["id_token"], gm["entry_ts"], False, gm["gender"],
                    gm["age"], gm["age_bucket"], group_id, group_size,
                    gm["is_face_hidden"]
                ))

            # ── Zone visits ──
            # Each visitor visits 1-4 zones
            num_zones = random.choices([1, 2, 3, 4], weights=[0.15, 0.35, 0.30, 0.20], k=1)[0]
            visited_zones = random.sample(ZONES, min(num_zones, len(ZONES)))
            current_ts = entry_ts + timedelta(seconds=random.uniform(15, 45))

            for zone_tuple in visited_zones:
                dwell_sec = random.uniform(20, 180)  # 20s to 3 min per zone
                enter_ts = current_ts
                exit_ts_zone = enter_ts + timedelta(seconds=dwell_sec)

                events.append(make_zone_entered(track_id, zone_tuple, enter_ts, gender, age, age_bucket))
                events.append(make_zone_exited(track_id, zone_tuple, exit_ts_zone, gender, age, age_bucket))

                # Group members also visit similar zones
                for gm in extra_members:
                    gm_enter = enter_ts + timedelta(seconds=random.uniform(2, 10))
                    gm_exit = gm_enter + timedelta(seconds=dwell_sec + random.uniform(-15, 15))
                    events.append(make_zone_entered(gm["track_id"], zone_tuple, gm_enter, gm["gender"], gm["age"], gm["age_bucket"]))
                    events.append(make_zone_exited(gm["track_id"], zone_tuple, gm_exit, gm["gender"], gm["age"], gm["age_bucket"]))

                current_ts = exit_ts_zone + timedelta(seconds=random.uniform(5, 20))

            # ── Billing queue (conversion ~35%) ──
            goes_to_billing = random.random() < 0.35
            if goes_to_billing:
                queue_position += 1
                if queue_position > 6:
                    queue_position = random.randint(1, 3)

                join_ts = current_ts + timedelta(seconds=random.uniform(5, 30))
                wait_sec = random.randint(5, 120)
                abandoned = random.random() < 0.12  # 12% abandon queue

                if abandoned:
                    served_ts = None
                    exit_ts_q = join_ts + timedelta(seconds=wait_sec)
                else:
                    served_ts = join_ts + timedelta(seconds=random.randint(3, 15))
                    exit_ts_q = served_ts + timedelta(seconds=random.randint(60, 200))

                events.append(make_queue_event(
                    track_id, join_ts, served_ts, exit_ts_q,
                    wait_sec, queue_position, abandoned,
                    gender, age, age_bucket
                ))

                # Group members also queue
                for gm in extra_members:
                    queue_position += 1
                    gm_join = join_ts + timedelta(seconds=random.uniform(2, 10))
                    gm_wait = random.randint(5, 100)
                    gm_abandoned = random.random() < 0.08
                    if gm_abandoned:
                        gm_served = None
                        gm_exit = gm_join + timedelta(seconds=gm_wait)
                    else:
                        gm_served = gm_join + timedelta(seconds=random.randint(3, 12))
                        gm_exit = gm_served + timedelta(seconds=random.randint(60, 180))
                    events.append(make_queue_event(
                        gm["track_id"], gm_join, gm_served, gm_exit,
                        gm_wait, queue_position, gm_abandoned,
                        gm["gender"], gm["age"], gm["age_bucket"]
                    ))

                current_ts = exit_ts_q + timedelta(seconds=random.uniform(10, 60))
            else:
                current_ts = current_ts + timedelta(seconds=random.uniform(30, 120))

            # ── EXIT event ──
            exit_ts_final = current_ts + timedelta(seconds=random.uniform(10, 60))
            events.append(make_exit_event(
                id_token, exit_ts_final, False, gender, age, age_bucket,
                group_id, group_size, is_face_hidden
            ))
            for gm in extra_members:
                gm_exit_final = exit_ts_final + timedelta(seconds=random.uniform(1, 15))
                events.append(make_exit_event(
                    gm["id_token"], gm_exit_final, False, gm["gender"],
                    gm["age"], gm["age_bucket"], group_id, group_size,
                    gm["is_face_hidden"]
                ))

            # ── Re-entry (~5% of visitors come back) ──
            if random.random() < 0.05:
                reentry_ts = exit_ts_final + timedelta(minutes=random.randint(15, 90))
                if reentry_ts.hour < CLOSE_HOUR:
                    events.append(make_entry_event(
                        id_token, reentry_ts, False, gender, age, age_bucket,
                        None, None, is_face_hidden
                    ))
                    # Quick revisit: 1 zone
                    revisit_zone = random.choice(ZONES)
                    rz_enter = reentry_ts + timedelta(seconds=random.uniform(15, 30))
                    rz_exit = rz_enter + timedelta(seconds=random.uniform(30, 120))
                    events.append(make_zone_entered(track_id, revisit_zone, rz_enter, gender, age, age_bucket))
                    events.append(make_zone_exited(track_id, revisit_zone, rz_exit, gender, age, age_bucket))

                    rexit_ts = rz_exit + timedelta(seconds=random.uniform(30, 90))
                    events.append(make_exit_event(
                        id_token, rexit_ts, False, gender, age, age_bucket,
                        None, None, is_face_hidden
                    ))

    # Sort all events by their timestamp
    def event_ts(e: dict) -> str:
        return e.get("event_timestamp") or e.get("event_time") or e.get("queue_join_ts", "")

    events.sort(key=event_ts)
    return events


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    events = simulate_day()

    output_path = Path(__file__).parent / "event_log.jsonl"
    with open(output_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Stats
    entry_count = sum(1 for e in events if e.get("event_type") == "entry")
    exit_count = sum(1 for e in events if e.get("event_type") == "exit")
    zone_enter = sum(1 for e in events if e.get("event_type") == "zone_entered")
    zone_exit = sum(1 for e in events if e.get("event_type") == "zone_exited")
    q_completed = sum(1 for e in events if e.get("event_type") == "queue_completed")
    q_abandoned = sum(1 for e in events if e.get("event_type") == "queue_abandoned")
    staff_count = sum(1 for e in events if e.get("is_staff") is True)
    group_events = sum(1 for e in events if e.get("group_id") is not None)

    print(f"✅ Generated {len(events)} events → {output_path}")
    print(f"   entry: {entry_count}  |  exit: {exit_count}")
    print(f"   zone_entered: {zone_enter}  |  zone_exited: {zone_exit}")
    print(f"   queue_completed: {q_completed}  |  queue_abandoned: {q_abandoned}")
    print(f"   staff events: {staff_count}  |  group events: {group_events}")
