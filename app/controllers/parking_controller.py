from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ParkingController:
    """
    Controller quản lý phân hệ Đỗ xe cá nhân tại các trạm Hub.
    """
    RESERVATION_TIMEOUT_MINUTES = 15

    def __init__(self, db_session):
        self.db = db_session

    def reserve_personal_slot(self, student_id: str, hub_id: str, slot_id: str, slot_obj: Optional[Any] = None) -> Dict[str, Any]:
        """
        Đặt trước ô đỗ xe cá nhân trong 15 phút.
        """
        if slot_obj:
            slot = slot_obj
        else:
            from app.entities.hub import ParkingSlot
            slot = self.db.query(ParkingSlot).filter(
                ParkingSlot.slot_id == slot_id,
                ParkingSlot.hub_id == hub_id,
                ParkingSlot.slot_type == "PERSONAL"
            ).first()

        if not slot or slot.status != "AVAILABLE":
            raise ValueError("Ô đỗ cá nhân không khả dụng hoặc đã được đặt chỗ.")

        slot.status = "RESERVED"
        
        expire_time = datetime.now() + timedelta(minutes=self.RESERVATION_TIMEOUT_MINUTES)
        reservation_id = f"RES_PARK_{slot_id}_{int(datetime.now().timestamp())}"

        if hasattr(self.db, "commit"):
            self.db.commit()

        return {
            "reservation_id": reservation_id,
            "student_id": student_id,
            "slot_id": slot_id,
            "hub_id": hub_id,
            "status": "RESERVED",
            "expires_at": expire_time.strftime("%Y-%m-%d %H:%M:%S")
        }