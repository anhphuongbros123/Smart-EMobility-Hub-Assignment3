from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class OverloadStatus(str, Enum):
    NORMAL = "NORMAL"                     
    OVERLOAD_WARNING = "OVERLOAD_WARNING" 
    OVERLOADED = "OVERLOADED"             


class RecommendationType(str, Enum):
    REBALANCE_VEHICLES = "REBALANCE_VEHICLES"
    EXPAND_SLOTS = "EXPAND_SLOTS"


@dataclass
class WhatIfScenario:
    demand_increase_pct: float
    forecast_horizon_hours: int = 24
    hub_ids: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.demand_increase_pct < 0:
            raise ValueError("demand_increase_pct must be >= 0.")
        if self.forecast_horizon_hours <= 0:
            raise ValueError("forecast_horizon_hours must be > 0.")
        if self.hub_ids is not None and len(self.hub_ids) == 0:
            raise ValueError("hub_ids must not be empty (use None for all hubs).")


@dataclass
class SimulationResult:
    hub_id: str
    capacity: int
    current_demand: int
    forecast_demand: int
    utilization_rate: float  # percent, rounded to 2 decimals
    status: OverloadStatus
    warning_threshold: float = 90.0  # per-hub threshold (Hub.overload_threshold)

    @property
    def is_at_risk(self) -> bool:
        return self.status != OverloadStatus.NORMAL

    def to_dict(self) -> dict:
        return {
            "hub_id": self.hub_id,
            "capacity": self.capacity,
            "current_demand": self.current_demand,
            "forecast_demand": self.forecast_demand,
            "utilization_rate": self.utilization_rate,
            "status": self.status.value,
            "warning_threshold": self.warning_threshold,
        }


@dataclass
class Recommendation:
    type: RecommendationType
    hub_id: str
    quantity: int
    target_hub_id: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "hub_id": self.hub_id,
            "target_hub_id": self.target_hub_id,
            "quantity": self.quantity,
            "reason": self.reason,
        }