import math
from typing import Dict, List, Optional

from app.entities.simulation_entities import (
    OverloadStatus,
    Recommendation,
    RecommendationType,
    SimulationResult,
    WhatIfScenario,
)


def _ceil(x: float) -> int:
    return math.ceil(round(x, 6))


def _floor(x: float) -> int:
    return math.floor(round(x, 6))


class SimulationController:
    OVERLOAD_WARNING_THRESHOLD = 90.0  
    OVERLOADED_THRESHOLD = 100.0      
    TARGET_UTILIZATION = 80.0          

    def __init__(self, hub_controller) -> None:
        self.hub_controller = hub_controller

    # ======== classification =========
    @classmethod
    def classify_overload(cls, utilization: float, warning_threshold: Optional[float] = None) -> OverloadStatus:
        threshold = (cls.OVERLOAD_WARNING_THRESHOLD
                     if warning_threshold is None else warning_threshold)
        if utilization > cls.OVERLOADED_THRESHOLD:
            return OverloadStatus.OVERLOADED
        if utilization >= threshold:
            return OverloadStatus.OVERLOAD_WARNING
        return OverloadStatus.NORMAL

    @classmethod
    def _target_ratio(cls, warning_threshold: float) -> float:
        return max(min(cls.TARGET_UTILIZATION, warning_threshold - 10.0), 10.0) / 100

    # ========= UC14: run_simulation ===========
    def run_simulation(self, scenario: WhatIfScenario, only_at_risk: bool = False) -> List[SimulationResult]:
        hubs = self.hub_controller.get_all_hubs()
        known = {h.hub_id for h in hubs}
        if scenario.hub_ids is None:
            affected = known
        else:
            unknown = [i for i in scenario.hub_ids if i not in known]
            if unknown:
                raise ValueError(f"Unknown hub id(s): {', '.join(unknown)}")
            affected = set(scenario.hub_ids)

        results: List[SimulationResult] = []
        for hub in hubs:
            growth = scenario.demand_increase_pct if hub.hub_id in affected else 0.0
            forecast = _ceil(hub.vehicle_count * (1 + growth / 100))
            raw_util = forecast / hub.capacity * 100
            results.append(SimulationResult(
                hub_id=hub.hub_id,
                capacity=hub.capacity,
                current_demand=hub.vehicle_count,
                forecast_demand=forecast,
                utilization_rate=round(raw_util, 2),
                status=self.classify_overload(raw_util, hub.warning_threshold),
                warning_threshold=hub.warning_threshold,
            ))
        results.sort(key=lambda r: (-r.utilization_rate, r.hub_id))
        if only_at_risk:
            results = [r for r in results if r.is_at_risk]
        return results

    # ========== UC15: export_recommendations ==========
    def export_recommendations(self, results: List[SimulationResult]) -> List[Recommendation]:
        spare: Dict[str, int] = {}
        for r in results:
            if r.status == OverloadStatus.NORMAL:
                t = self._target_ratio(r.warning_threshold)
                room = _floor(r.capacity * t - r.forecast_demand)
                if room > 0:
                    spare[r.hub_id] = room

        recs: List[Recommendation] = []
        at_risk = sorted((r for r in results if r.is_at_risk),
                         key=lambda r: (-r.utilization_rate, r.hub_id))
        for hub in at_risk:
            target = self._target_ratio(hub.warning_threshold)
            excess = _ceil(hub.forecast_demand - hub.capacity * target)
            remaining_demand = hub.forecast_demand
            for donor_id in sorted(spare, key=lambda k: (-spare[k], k)):
                if excess <= 0:
                    break
                move = min(excess, spare[donor_id])
                if move <= 0:
                    continue
                recs.append(Recommendation(
                    type=RecommendationType.REBALANCE_VEHICLES,
                    hub_id=hub.hub_id, target_hub_id=donor_id, quantity=move,
                    reason=f"{hub.hub_id} is {hub.status.value} "
                           f"({hub.utilization_rate}%); {donor_id} has spare capacity.",
                ))
                spare[donor_id] -= move
                excess -= move
                remaining_demand -= move
            if excess > 0:
                extra = _ceil(remaining_demand / target) - hub.capacity
                recs.append(Recommendation(
                    type=RecommendationType.EXPAND_SLOTS,
                    hub_id=hub.hub_id, quantity=extra,
                    reason=f"{hub.hub_id} is {hub.status.value}; no hub can absorb "
                           f"the remaining {excess} vehicle(s).",
                ))
        return recs