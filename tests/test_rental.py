import pytest
from datetime import datetime, timedelta
from app.controllers.rental_controller import RentalController


@pytest.fixture
def controller():
    return RentalController()


@pytest.fixture
def sample_vehicle():
    return {"id": "VEH-001", "status": "AVAILABLE", "battery_level": 85}


@pytest.fixture
def sample_slot():
    return {"id": "SLOT-01", "hub_id": "HUB-BK", "status": "AVAILABLE"}


def test_reserve_vehicle_success(controller, sample_vehicle):
    """Kiểm tra đặt xe thành công và xe đổi sang RESERVED"""
    res = controller.reserve_vehicle("SV2026", sample_vehicle)
    assert res["status"] == "PENDING"
    assert sample_vehicle["status"] == "RESERVED"
    assert len(res["pin_code"]) == 4


def test_reserve_vehicle_low_battery(controller):
    """Kiểm tra chặn xe pin dưới 20%"""
    low_battery_vehicle = {"id": "VEH-002", "status": "AVAILABLE", "battery_level": 15}
    with pytest.raises(ValueError, match="Mức pin không đủ"):
        controller.reserve_vehicle("SV2026", low_battery_vehicle)


def test_unlock_with_wrong_pin(controller, sample_vehicle):
    """Kiểm tra ném lỗi khi nhập sai mã PIN"""
    res = controller.reserve_vehicle("SV2026", sample_vehicle)
    with pytest.raises(ValueError, match="Mã PIN xác thực không chính xác"):
        controller.unlock_and_start_trip(res, sample_vehicle, input_pin="0000")


def test_unlock_expired_reservation(controller, sample_vehicle):
    """Kiểm tra hết hạn 15 phút: xe trả về AVAILABLE và ném lỗi TimeoutError"""
    res = controller.reserve_vehicle("SV2026", sample_vehicle)
    # Giả lập thời gian sau 16 phút
    current_time = res["reserved_at"] + timedelta(minutes=16)

    with pytest.raises(TimeoutError, match="hết hạn 15 phút"):
        controller.unlock_and_start_trip(res, sample_vehicle, res["pin_code"], current_time=current_time)

    assert sample_vehicle["status"] == "AVAILABLE"
    assert res["status"] == "EXPIRED"


def test_calculate_fare_long_trip_no_idle(controller):
    """Đi xa 10km, dừng 3 phút (<5p miễn phí) -> Chỉ tính cước km"""
    # 10.000 + (10 * 2.500) = 35.000 VNĐ
    res = controller.calculate_fare(distance_km=10.0, idle_minutes=3)
    assert res["idle_fee"] == 0.0
    assert res["total_fare"] == 35000.0


def test_calculate_fare_excessive_idle_penalty(controller):
    """Đi 2km, dừng chiếm xe 14 phút -> Phạt lũy tiến"""
    # Dừng 14 phút -> Trừ 5p free = 9p tính phí.
    # 5p đầu (phút 6-10): 5 * 1000 = 5000
    # 4p sau (phút 11-14): 4 * (1000 * 1.5) = 6000 -> idle_fee = 11000
    # Tổng: 10.000 + 2*2500 + 11.000 = 26.000 VNĐ
    res = controller.calculate_fare(distance_km=2.0, idle_minutes=14)
    assert res["idle_fee"] == 11000.0
    assert res["total_fare"] == 26000.0


def test_return_vehicle_success(controller, sample_vehicle, sample_slot):
    """Kiểm tra trả xe thành công: ô đỗ khóa, xe về AVAILABLE"""
    res = controller.reserve_vehicle("SV2026", sample_vehicle)
    trip = controller.unlock_and_start_trip(res, sample_vehicle, res["pin_code"])

    receipt = controller.return_vehicle(trip, sample_vehicle, sample_slot, distance_km=4.0, idle_minutes=2)
    assert receipt["status"] == "COMPLETED"
    assert sample_vehicle["status"] == "AVAILABLE"
    assert sample_slot["status"] == "OCCUPIED"