import datetime
from sqlalchemy.orm import Session
from app.entities import DispatchOrder, Vehicle, Hub

class RebalanceController:
    def __init__(self, db: Session):
        self.db = db

    def create_rebalance_order(self, source_hub_id: str, dest_hub_id: str, vehicle_id: str, operator_id: str = "OP_01", quantity: int = 1) -> DispatchOrder:
        """Khởi tạo lệnh luân chuyển phương tiện giữa 2 trạm Hub."""
        if source_hub_id == dest_hub_id:
            raise ValueError("Trạm nguồn và trạm đích không được trùng nhau.")

        vehicle = self.db.query(Vehicle).filter(
            Vehicle.vehicle_id == vehicle_id,
            Vehicle.current_hub_id == source_hub_id
        ).first()

        if not vehicle:
            raise ValueError("Không tìm thấy phương tiện tại trạm nguồn.")
        if vehicle.status != "AVAILABLE":
            raise ValueError(f"Phương tiện không ở trạng thái AVAILABLE (Hiện tại: {vehicle.status}).")

        dest_hub = self.db.query(Hub).filter(Hub.hub_id == dest_hub_id).first()
        if not dest_hub:
            raise ValueError("Trạm đích không tồn tại trên hệ thống.")

        order_id = f"ORD_{int(datetime.datetime.utcnow().timestamp() * 1000)}"
        order = DispatchOrder(
            order_id=order_id,
            operator_id=str(operator_id),
            source_hub_id=source_hub_id,
            dest_hub_id=dest_hub_id,
            quantity=quantity,
            status="PENDING"
        )

        vehicle.status = "IN_TRANSIT"

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order