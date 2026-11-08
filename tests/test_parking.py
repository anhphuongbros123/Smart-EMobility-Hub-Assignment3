import pytest
from unittest.mock import MagicMock
from app.controllers.parking_controller import ParkingController
from app.controllers.charging_controller import ChargingController

def test_reserve_personal_slot_success():
    """TC01: Đặt trước ô đỗ cá nhân thành công trong 15 phút."""
    mock_db = MagicMock()
    mock_slot = MagicMock(slot_id="P_SLOT_01", hub_id="HUB_DHBK", slot_type="PERSONAL", status="AVAILABLE")
    
    controller = ParkingController(mock_db)
    result = controller.reserve_personal_slot("SV241001", "HUB_DHBK", "P_SLOT_01", slot_obj=mock_slot)

    assert result["slot_id"] == "P_SLOT_01"
    assert result["status"] == "RESERVED"
    assert mock_slot.status == "RESERVED"

def test_reserve_personal_slot_unavailable_raises_error():
    """TC02: Bắt lỗi khi ô đỗ cá nhân đã bị giữ hoặc không khả dụng."""
    mock_db = MagicMock()
    mock_slot = MagicMock(slot_id="P_SLOT_01", hub_id="HUB_DHBK", slot_type="PERSONAL", status="OCCUPIED")
    
    controller = ParkingController(mock_db)
    with pytest.raises(ValueError, match="Ô đỗ cá nhân không khả dụng"):
        controller.reserve_personal_slot("SV241001", "HUB_DHBK", "P_SLOT_01", slot_obj=mock_slot)

def test_calculate_charging_fee_correctly():
    """TC03: Kích hoạt sạc và tính tiền chính xác theo số kWh tiêu thụ (3.000 VNĐ/kWh)."""
    mock_db = MagicMock()
    mock_port = MagicMock(port_id="PORT_QR_01", status="AVAILABLE")
    
    charging_ctrl = ChargingController(mock_db)
    start_res = charging_ctrl.start_charging("SV241001", "PORT_QR_01", port_obj=mock_port)
    
    assert start_res["status"] == "CHARGING"
    assert mock_port.status == "CHARGING"

    stop_res = charging_ctrl.stop_charging(start_res["session_id"], kwh_consumed=12.5, port_obj=mock_port)
    
    assert stop_res["kwh_consumed"] == 12.5
    assert stop_res["total_fee"] == 37500.0
    assert stop_res["status"] == "COMPLETED"
    assert mock_port.status == "AVAILABLE"

def test_charging_with_invalid_kwh_raises_error():
    """TC04: Bắt lỗi ngoại lệ khi số kWh tiêu thụ là số âm."""
    mock_db = MagicMock()
    charging_ctrl = ChargingController(mock_db)
    
    with pytest.raises(ValueError, match="không được là số âm"):
        charging_ctrl.stop_charging("SESS_TEST", kwh_consumed=-5.0)