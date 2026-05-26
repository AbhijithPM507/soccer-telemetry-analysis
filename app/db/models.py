import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)

    telemetry_events = relationship("TelemetryEvent", back_populates="match")


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(String, ForeignKey("matches.id"), nullable=False, index=True)
    player_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    coord_x = Column(Float, nullable=False)
    coord_y = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    match = relationship("Match", back_populates="telemetry_events")
