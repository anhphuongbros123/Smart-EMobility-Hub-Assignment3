from sqlalchemy import Column, Integer, Numeric, String
from app.database import Base


class Hub(Base):
    __tablename__ = "mobility_hubs"

    hub_id = Column(String(20), primary_key=True)
    hub_name = Column(String(100), nullable=False)
    latitude = Column(Numeric(10, 6), nullable=False)
    longitude = Column(Numeric(10, 6), nullable=False)
    total_slots = Column(Integer, default=0)
    total_ports = Column(Integer, default=0)
    overload_threshold = Column(Integer, default=90)
    status = Column(String(20), default="ACTIVE")