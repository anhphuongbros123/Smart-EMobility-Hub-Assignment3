from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.controllers.hub_controller import HubController
from app.controllers.simulation_controller import SimulationController
from app.database import get_db
from app.entities.simulation_entities import WhatIfScenario

router = APIRouter(prefix="/api/simulation", tags=["What-If Simulation"])


def get_simulation_controller(db: Session = Depends(get_db)) -> SimulationController:
    return SimulationController(HubController(db))


class ScenarioRequest(BaseModel):
    demand_increase_pct: float = Field(ge=0, description="Demand growth in %")
    forecast_horizon_hours: int = Field(default=24, gt=0)
    hub_ids: Optional[List[str]] = None


def _simulate(ctrl: SimulationController, req: ScenarioRequest):
    try:
        scenario = WhatIfScenario(req.demand_increase_pct,
                                  req.forecast_horizon_hours, req.hub_ids)
        return ctrl.run_simulation(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/hubs")
def list_hubs(ctrl: SimulationController = Depends(get_simulation_controller)):
    return [{"hub_id": h.hub_id, "capacity": h.capacity,
             "vehicle_count": h.vehicle_count,
             "warning_threshold": h.warning_threshold}
            for h in ctrl.hub_controller.get_all_hubs()]


@router.post("/run")
def run_simulation(req: ScenarioRequest,
                   ctrl: SimulationController = Depends(get_simulation_controller)):
    results = _simulate(ctrl, req)
    return {
        "results": [r.to_dict() for r in results],
        "at_risk_count": sum(1 for r in results if r.is_at_risk),
    }


@router.post("/recommendations")
def get_recommendations(req: ScenarioRequest,
                        ctrl: SimulationController = Depends(get_simulation_controller)):
    results = _simulate(ctrl, req)
    recs = ctrl.export_recommendations(results)
    return {
        "results": [r.to_dict() for r in results],
        "recommendations": [r.to_dict() for r in recs],
    }