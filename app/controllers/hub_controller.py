from dataclasses import dataclass
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.entities.hub import Hub
from app.entities.vehicle import Vehicle


@dataclass
class HubInfo:
    hub_id: str
    capacity: int
    vehicle_count: int
    warning_threshold: float = 90.0

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("Hub capacity must be > 0.")
        if self.vehicle_count < 0:
            raise ValueError("Vehicle count must be >= 0.")
        if not 0 < self.warning_threshold <= 100:
            raise ValueError("warning_threshold must be in (0, 100].")


class HubController:
    OCCUPYING_STATUSES = ("AVAILABLE", "RESERVED", "CHARGING")

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_hubs(self) -> List[HubInfo]:
        """ACTIVE hubs with total_slots > 0, plus their parked-vehicle count."""
        rows = (
            self.db.query(Vehicle.current_hub_id, func.count(Vehicle.vehicle_id))
            .filter(Vehicle.status.in_(self.OCCUPYING_STATUSES))
            .group_by(Vehicle.current_hub_id)
            .all()
        )
        counts = {hub_id: n for hub_id, n in rows}
        hubs = (
            self.db.query(Hub).filter(Hub.status == "ACTIVE")
            .order_by(Hub.hub_id).all()
        )
        result = []
        for h in hubs:
            if not h.total_slots or h.total_slots <= 0:
                continue  # cannot compute utilization without capacity
            result.append(HubInfo(
                hub_id=h.hub_id,
                capacity=h.total_slots,
                vehicle_count=counts.get(h.hub_id, 0),
                warning_threshold=float(h.overload_threshold or 90),
            ))
        return result

    def get_hub(self, hub_id: str) -> HubInfo:
        for h in self.get_all_hubs():
            if h.hub_id == hub_id:
                return h
        raise ValueError(f"Hub '{hub_id}' not found.")