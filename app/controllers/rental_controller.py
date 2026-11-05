from datetime import datetime, timedelta
import random


class RentalController:
    def __init__(self):
        # Định mức cước và cấu hình hệ thống
        self.BASE_FARE = 10000          # 10.000 VNĐ phí mở khóa / khởi động
        self.KM_RATE = 2500             # 2.500 VNĐ / km di chuyển
        self.MINUTE_RATE = 1000         # 1.000 VNĐ / phút dừng đỗ
        self.FREE_IDLE_LIMIT = 5        # 5 phút miễn phí dừng (chờ đèn đỏ, dừng tạm)
        self.PENALTY_IDLE_LIMIT = 10    # Ngưỡng bắt đầu nhân hệ số phạt dừng đỗ
        self.RESERVATION_MINUTES = 15   # Giới hạn giữ xe 15 phút
        self.MIN_BATTERY = 20           # Mức pin tối thiểu để thuê (%)

    def reserve_vehicle(self, student_id: str, vehicle: dict) -> dict:
        """
        Đặt giữ chỗ xe trước 15 phút kèm mã PIN ngẫu nhiên.
        """
        if vehicle.get("status") != "AVAILABLE":
            raise ValueError("Xe không khả dụng để đặt giữ chỗ.")

        if vehicle.get("battery_level", 0) < self.MIN_BATTERY:
            raise ValueError("Mức pin không đủ điều kiện vận hành (dưới 20%).")

        now = datetime.now()
        pin_code = f"{random.randint(1000, 9999)}"
        expires_at = now + timedelta(minutes=self.RESERVATION_MINUTES)

        # Cập nhật trạng thái đối tượng xe
        vehicle["status"] = "RESERVED"

        return {
            "reservation_id": f"RES-{vehicle.get('id')}-{int(now.timestamp())}",
            "student_id": student_id,
            "vehicle_id": vehicle.get("id"),
            "pin_code": pin_code,
            "reserved_at": now,
            "expires_at": expires_at,
            "status": "PENDING"
        }

    def unlock_and_start_trip(self, reservation: dict, vehicle: dict, input_pin: str, current_time: datetime = None) -> dict:
        """
        Mở khóa chốt vật lý và bắt đầu chuyến đi.
        Kiểm tra mã PIN và hạn giữ chỗ 15 phút tại Backend.
        """
        if current_time is None:
            current_time = datetime.now()

        # Kiểm tra quá hạn 15 phút
        if current_time > reservation["expires_at"]:
            vehicle["status"] = "AVAILABLE"
            reservation["status"] = "EXPIRED"
            raise TimeoutError("Phiên đặt chỗ đã hết hạn 15 phút.")

        # Kiểm tra khớp mã PIN
        if input_pin != reservation["pin_code"]:
            raise ValueError("Mã PIN xác thực không chính xác.")

        # Cập nhật trạng thái xe và khởi tạo chuyến đi
        vehicle["status"] = "IN_USE"
        reservation["status"] = "ACTIVATED"

        return {
            "trip_id": f"TRIP-{vehicle.get('id')}-{int(current_time.timestamp())}",
            "student_id": reservation["student_id"],
            "vehicle_id": vehicle.get("id"),
            "start_time": current_time,
            "status": "IN_PROGRESS"
        }

    def calculate_fare(self, distance_km: float, idle_minutes: int) -> dict:
        """
        Tính cước chuyến đi theo mô hình dừng đỗ lũy tiến (Dynamic Idle-Time Pricing):
        - Miễn phí 5 phút dừng đầu tiên.
        - Dừng từ phút thứ 6 đến 10 tính 1.0x MINUTE_RATE.
        - Dừng trên 10 phút phạt 1.5x MINUTE_RATE.
        """
        if distance_km < 0 or idle_minutes < 0:
            raise ValueError("Quãng đường và thời gian dừng không được âm.")

        # 1. Cước di chuyển theo km
        distance_fee = distance_km * self.KM_RATE

        # 2. Phí dừng đỗ / chiếm dụng xe
        idle_fee = 0.0
        if idle_minutes > self.FREE_IDLE_LIMIT:
            billable_idle = idle_minutes - self.FREE_IDLE_LIMIT
            tier_limit = self.PENALTY_IDLE_LIMIT - self.FREE_IDLE_LIMIT

            if billable_idle <= tier_limit:
                idle_fee = billable_idle * self.MINUTE_RATE
            else:
                standard_idle_fee = tier_limit * self.MINUTE_RATE
                over_penalty_minutes = billable_idle - tier_limit
                penalty_idle_fee = over_penalty_minutes * (self.MINUTE_RATE * 1.5)
                idle_fee = standard_idle_fee + penalty_idle_fee

        total_fare = self.BASE_FARE + distance_fee + idle_fee

        return {
            "base_fare": float(self.BASE_FARE),
            "distance_fee": float(distance_fee),
            "idle_fee": float(idle_fee),
            "total_fare": float(total_fare),
            "idle_minutes_billed": max(0, idle_minutes - self.FREE_IDLE_LIMIT)
        }

    def return_vehicle(self, trip: dict, vehicle: dict, slot: dict, distance_km: float, idle_minutes: int) -> dict:
        """
        Trả xe tại trạm, khóa chốt và chốt hóa đơn.
        """
        if slot.get("status") != "AVAILABLE":
            raise ValueError("Ô đỗ không khả dụng hoặc đã có xe đỗ.")

        fare_breakdown = self.calculate_fare(distance_km, idle_minutes)

        # Chuyển trạng thái
        vehicle["status"] = "AVAILABLE"
        slot["status"] = "OCCUPIED"
        trip["status"] = "COMPLETED"
        trip["end_time"] = datetime.now()

        return {
            "trip_id": trip.get("trip_id"),
            "vehicle_id": vehicle.get("id"),
            "slot_id": slot.get("id"),
            "fare": fare_breakdown,
            "status": "COMPLETED"
        }