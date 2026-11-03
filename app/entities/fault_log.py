import datetime
from sqlalchemy import Column, DateTime, String, Text
from app.database import Base


class FaultLog(Base):
    __tablename__ = "fault_logs"

    incident_id = Column(String(20), primary_key=True)
    reporter_id = Column(String(20), nullable=False)
    equipment_id = Column(String(20), nullable=False)
    issue_type = Column(String(50), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="OPEN")
    reported_at = Column(DateTime, default=datetime.datetime.utcnow)