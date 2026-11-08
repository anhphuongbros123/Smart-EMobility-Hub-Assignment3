from datetime import datetime
from typing import Dict, Any, Optional

class ChargingController:
    """
    Controller quản lý phân hệ Trạm sạc QR và tính cước điện năng.
    """
    PRICE_PER_KWH = 3000.0 

    def __init__(self, db_session):
        self.db = db_session

    def start_charging(self, student_id: str, port_id: str, port_obj: Optional[Any] = None) -> Dict[str, Any]:
        """
        Kích hoạt relay cấp điện khi quét mã QR cổng sạc thành công.
        """
        if port_obj:
            port = port_obj
        else:
            from app.entities.hub import ChargingPort
            port = self.db.query(ChargingPort).filter(ChargingPort.port_id == port_id).first()

        if not port or port.status != "AVAILABLE":
            raise ValueError("Cổng sạc không khả dụng hoặc đang gặp sự cố kỹ thuật.")

        port.status = "CHARGING"
        session_id = f"SESS_CHG_{port_id}_{int(datetime.now().timestamp())}"

        if hasattr(self.db, "commit"):
            self.db.commit()

        return {
            "session_id": session_id,
            "student_id": student_id,
            "port_id": port_id,
            "status": "CHARGING",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def stop_charging(self, session_id: str, kwh_consumed: float, port_obj: Optional[Any] = None) -> Dict[str, Any]:
        """
        Ngắt nguồn điện, chốt số kWh tiêu thụ và tính toán tổng tiền sạc.
        """
        if kwh_consumed < 0:
            raise ValueError("Số điện năng tiêu thụ (kWh) không được là số âm.")

        total_fee = round(kwh_consumed * self.PRICE_PER_KWH, 2)

        if port_obj:
            port_obj.status = "AVAILABLE"
        
        if hasattr(self.db, "commit"):
            self.db.commit()

        return {
            "session_id": session_id,
            "kwh_consumed": kwh_consumed,
            "total_fee": total_fee,
            "status": "COMPLETED",
            "end_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }