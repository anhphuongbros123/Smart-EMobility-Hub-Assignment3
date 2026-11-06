import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.database import Base


class DispatchOrder(Base):
    __tablename__ = "dispatch_orders"

    order_id = Column(String(20), primary_key=True)
    operator_id = Column(String(20), nullable=False)
    source_hub_id = Column(
        String(20), ForeignKey("mobility_hubs.hub_id"), nullable=False
    )
    dest_hub_id = Column(
        String(20), ForeignKey("mobility_hubs.hub_id"), nullable=False
    )
    quantity = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)