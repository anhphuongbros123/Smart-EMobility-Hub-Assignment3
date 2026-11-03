from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id = Column(String(20), primary_key=True)
    current_hub_id = Column(String(20), ForeignKey("mobility_hubs.hub_id"))
    vehicle_type = Column(String(20), nullable=False)
    battery_soc = Column(Integer)
    is_locked = Column(Boolean, default=True)
    status = Column(String(20), default="AVAILABLE")