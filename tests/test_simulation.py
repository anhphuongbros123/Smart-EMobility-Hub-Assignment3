import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.entities
from app.controllers.hub_controller import HubController, HubInfo
from app.controllers.simulation_controller import SimulationController
from app.database import Base
from app.entities.hub import Hub
from app.entities.simulation_entities import (
    OverloadStatus, RecommendationType, WhatIfScenario)
from app.entities.vehicle import Vehicle


# ---------------- helpers ----------------
class FakeHubController:
    def __init__(self, hubs):
        self._hubs = hubs

    def get_all_hubs(self):
        return list(self._hubs)


@pytest.fixture
def controller():
    return SimulationController(FakeHubController([
        HubInfo("H1", 100, 80), HubInfo("H2", 100, 20), HubInfo("H3", 10, 5)]))


def single_hub_controller(capacity, vehicles, threshold=90.0):
    return SimulationController(FakeHubController(
        [HubInfo("X", capacity, vehicles, threshold)]))


def add_hub(db, hub_id, slots, vehicles, status="ACTIVE", threshold=90,
            vehicle_status="AVAILABLE"):
    db.add(Hub(hub_id=hub_id, hub_name=hub_id, latitude=10.0, longitude=106.0,
               total_slots=slots, overload_threshold=threshold, status=status))
    for i in range(vehicles):
        db.add(Vehicle(vehicle_id=f"{hub_id}-{vehicle_status}-{i}",
                       current_hub_id=hub_id, vehicle_type="E-BIKE",
                       battery_soc=90, status=vehicle_status))


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    add_hub(session, "H1", 100, 80)
    add_hub(session, "H2", 100, 20)
    add_hub(session, "H3", 10, 5)
    session.commit()
    yield session
    session.close()


# ---------------- classification ----------------
@pytest.mark.parametrize("util,expected", [
    (89.0, OverloadStatus.NORMAL),
    (89.99, OverloadStatus.NORMAL),
    (90.0, OverloadStatus.OVERLOAD_WARNING),
    (100.0, OverloadStatus.OVERLOAD_WARNING),
    (100.01, OverloadStatus.OVERLOADED),
])
def test_classify_overload_thresholds(util, expected):
    assert SimulationController.classify_overload(util) == expected


def test_classify_uses_custom_hub_threshold():
    assert SimulationController.classify_overload(
        75.0, warning_threshold=70) == OverloadStatus.OVERLOAD_WARNING
    assert SimulationController.classify_overload(
        75.0, warning_threshold=90) == OverloadStatus.NORMAL


# ---------------- run_simulation ----------------
def test_run_simulation_forecast_and_utilization(controller):
    res = controller.run_simulation(WhatIfScenario(10))
    by_id = {r.hub_id: r for r in res}
    assert by_id["H1"].forecast_demand == 88
    assert by_id["H1"].utilization_rate == 88.0
    assert by_id["H3"].forecast_demand == 6          # ceil(5.5)
    assert [r.hub_id for r in res] == ["H1", "H3", "H2"]


def test_run_simulation_only_affected_hubs_grow(controller):
    res = controller.run_simulation(WhatIfScenario(25, hub_ids=["H1"]))
    by_id = {r.hub_id: r for r in res}
    assert by_id["H1"].utilization_rate == 100.0
    assert by_id["H1"].status == OverloadStatus.OVERLOAD_WARNING
    assert by_id["H2"].forecast_demand == 20


def test_run_simulation_overloaded_and_float_noise(controller):
    res = controller.run_simulation(WhatIfScenario(30, hub_ids=["H1"]))
    h1 = next(r for r in res if r.hub_id == "H1")
    assert h1.forecast_demand == 104                  # not 105
    assert h1.status == OverloadStatus.OVERLOADED


def test_run_simulation_only_at_risk_filter(controller):
    res = controller.run_simulation(WhatIfScenario(30, hub_ids=["H1"]), only_at_risk=True)
    assert [r.hub_id for r in res] == ["H1"]


def test_per_hub_threshold_applied():
    res = single_hub_controller(100, 70, threshold=70).run_simulation(WhatIfScenario(0))
    assert res[0].status == OverloadStatus.OVERLOAD_WARNING


# ---------------- invalid input ----------------
def test_zero_capacity_rejected():
    with pytest.raises(ValueError):
        HubInfo("Z", 0, 0)


def test_unknown_hub_rejected(controller):
    with pytest.raises(ValueError, match="Unknown hub"):
        controller.run_simulation(WhatIfScenario(10, hub_ids=["NOPE"]))


@pytest.mark.parametrize("kwargs", [
    {"demand_increase_pct": -5},
    {"demand_increase_pct": 10, "forecast_horizon_hours": 0},
    {"demand_increase_pct": 10, "hub_ids": []},
])
def test_invalid_scenario_rejected(kwargs):
    with pytest.raises(ValueError):
        WhatIfScenario(**kwargs)


# ---------------- export_recommendations ----------------
def test_recommend_rebalance_to_hub_with_spare_room(controller):
    recs = controller.export_recommendations(
        controller.run_simulation(WhatIfScenario(30, hub_ids=["H1"])))
    assert len(recs) == 1
    r = recs[0]
    assert r.type == RecommendationType.REBALANCE_VEHICLES
    assert (r.hub_id, r.target_hub_id, r.quantity) == ("H1", "H2", 24)


def test_recommend_expand_slots_when_no_donor():
    ctrl = single_hub_controller(100, 80)
    recs = ctrl.export_recommendations(ctrl.run_simulation(WhatIfScenario(30)))
    assert len(recs) == 1
    assert recs[0].type == RecommendationType.EXPAND_SLOTS
    assert recs[0].quantity == 30                     # ceil(104/0.8)=130 -> +30


def test_recommend_nothing_when_all_normal(controller):
    assert controller.export_recommendations(
        controller.run_simulation(WhatIfScenario(0))) == []


def test_recommendation_output_format(controller):
    res = controller.run_simulation(WhatIfScenario(30, hub_ids=["H1"]))
    d = controller.export_recommendations(res)[0].to_dict()
    assert set(d) == {"type", "hub_id", "target_hub_id", "quantity", "reason"}
    assert d["type"] == "REBALANCE_VEHICLES"


# ---------------- HubController + real DB ----------------
def test_hub_controller_reads_db(db):
    hubs = {h.hub_id: h for h in HubController(db).get_all_hubs()}
    assert hubs["H1"].capacity == 100 and hubs["H1"].vehicle_count == 80
    assert hubs["H3"].vehicle_count == 5


def test_hub_controller_filters_inactive_and_zero_slot_hubs(db):
    add_hub(db, "OFF", 50, 5, status="INACTIVE")
    add_hub(db, "ZERO", 0, 0)
    db.commit()
    ids = [h.hub_id for h in HubController(db).get_all_hubs()]
    assert "OFF" not in ids and "ZERO" not in ids


def test_hub_controller_ignores_in_use_and_faulty_vehicles(db):
    add_hub(db, "H9", 20, 3)
    add_hub(db, "H9b", 20, 0)
    for i, st in enumerate(["IN_USE", "FAULTY", "CHARGING"]):
        db.add(Vehicle(vehicle_id=f"X{i}", current_hub_id="H9", vehicle_type="E-BIKE",
                       battery_soc=50, status=st))
    db.commit()
    h9 = HubController(db).get_hub("H9")
    assert h9.vehicle_count == 3 + 1                  # 3 AVAILABLE + 1 CHARGING


def test_hub_controller_reads_custom_threshold(db):
    add_hub(db, "H8", 100, 70, threshold=70)
    db.commit()
    res = SimulationController(HubController(db)).run_simulation(
        WhatIfScenario(0, hub_ids=["H8"]))
    h8 = next(r for r in res if r.hub_id == "H8")
    assert h8.status == OverloadStatus.OVERLOAD_WARNING


def test_simulation_end_to_end_with_db(db):
    ctrl = SimulationController(HubController(db))
    recs = ctrl.export_recommendations(
        ctrl.run_simulation(WhatIfScenario(30, hub_ids=["H1"])))
    assert [(r.hub_id, r.target_hub_id, r.quantity) for r in recs] == [("H1", "H2", 24)]


# ---------------- API (boundary) ----------------
def test_api_run_and_recommendations(db):
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    try:
        client = TestClient(app)
        assert len(client.get("/api/simulation/hubs").json()) == 3

        r = client.post("/api/simulation/run", json={"demand_increase_pct": 30})
        assert r.status_code == 200
        assert r.json()["at_risk_count"] == 1          # only H1 (104%)

        r = client.post("/api/simulation/recommendations",
                        json={"demand_increase_pct": 30, "hub_ids": ["H1"]})
        rec = r.json()["recommendations"][0]
        assert (rec["hub_id"], rec["target_hub_id"], rec["quantity"]) == ("H1", "H2", 24)

        assert client.post("/api/simulation/run",
                           json={"demand_increase_pct": -1}).status_code == 422
        assert client.post("/api/simulation/run",
                           json={"demand_increase_pct": 10,
                                 "hub_ids": ["NOPE"]}).status_code == 400
    finally:
        app.dependency_overrides.clear()