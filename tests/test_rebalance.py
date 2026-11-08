import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.entities import Hub, Vehicle, DispatchOrder, FaultLog
from app.controllers.rebalance_controller import RebalanceController
from app.controllers.incident_controller import IncidentController

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_rebalance_order_success(db_session):
    hub_a = Hub(hub_id="HUB_A", hub_name="Hub KTX A", latitude=10.87, longitude=106.80, total_slots=10)
    hub_b = Hub(hub_id="HUB_B", hub_name="Hub KTX B", latitude=10.88, longitude=106.81, total_slots=10)
    vehicle = Vehicle(vehicle_id="VEH_001", current_hub_id="HUB_A", vehicle_type="E-BIKE", battery_soc=90, status="AVAILABLE")
    
    db_session.add_all([hub_a, hub_b, vehicle])
    db_session.commit()

    rebalance_ctrl = RebalanceController(db_session)
    order = rebalance_ctrl.create_rebalance_order("HUB_A", "HUB_B", "VEH_001", operator_id="OP_01")

    assert order.order_id is not None
    assert order.status == "PENDING"
    assert vehicle.status == "IN_TRANSIT"

def test_lock_faulty_equipment_vehicle(db_session):
    vehicle = Vehicle(vehicle_id="VEH_002", vehicle_type="E-BIKE", battery_soc=50, status="AVAILABLE")
    db_session.add(vehicle)
    db_session.commit()

    incident_ctrl = IncidentController(db_session)
    log = incident_ctrl.lock_faulty_equipment("VEHICLE", "VEH_002", "Lỗi pin sụt nhanh", reported_by="OP_01")

    assert log.incident_id is not None
    assert log.status == "OPEN"
    assert vehicle.status == "FAULTY"