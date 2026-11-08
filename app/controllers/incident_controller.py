import datetime
from sqlalchemy.orm import Session
from app.entities import Vehicle, Hub, FaultLog

class IncidentController:
    def __init__(self, db: Session):
        self.db = db

    def lock_faulty_equipment(self, equipment_type: str, equipment_id: str, description: str = None, reported_by: str = "SYSTEM") -> FaultLog:
        """Khóa thiết bị hỏng sang trạng thái FAULTY và khởi tạo FaultLog."""
        eq_type = equipment_type.upper()
        if eq_type not in ["VEHICLE", "HUB"]:
            raise ValueError("Loại thiết bị không hợp lệ.")

        if eq_type == "VEHICLE":
            equipment = self.db.query(Vehicle).filter(Vehicle.vehicle_id == equipment_id).first()
            if not equipment:
                raise ValueError("Không tìm thấy phương tiện.")
            equipment.status = "FAULTY"

        elif eq_type == "HUB":
            equipment = self.db.query(Hub).filter(Hub.hub_id == equipment_id).first()
            if not equipment:
                raise ValueError("Không tìm thấy trạm.")
            equipment.status = "FAULTY"

        incident_id = f"INC_{int(datetime.datetime.utcnow().timestamp() * 1000)}"
        fault_log = FaultLog(
            incident_id=incident_id,
            reporter_id=reported_by,
            equipment_id=equipment_id,
            issue_type=eq_type,
            description=description,
            status="OPEN"
        )

        self.db.add(fault_log)
        self.db.commit()
        self.db.refresh(fault_log)
        return fault_log