"""Database models for the athlete service."""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


class Athlete(Base):
    """Represents an athlete with personal and sports information."""
    __tablename__ = "athlete"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    country = Column(String, index=True)
    birth_date = Column(Date, index=True)
    height = Column(Integer, index=True)
    weight = Column(Integer, index=True)
    sport = Column(String, index=True)
    nick_name = Column(String, index=True)
    bio = Column(Text, index=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    deleted_at = Column(DateTime, nullable=True)


# Pydantic models for API
class AthleteBase(BaseModel):
    """Base class for all athletes."""
    # Personal Data
    name: str
    country: str
    birth_date: date
    height: int
    weight: int

    # Career Data
    sport: str
    nick_name: str
    bio: str

    class Config:
        from_attributes = True


class AthletePublic(AthleteBase):
    """Represents an athlete with public information."""
    id: int
    name: str
    country: str
    sport: str
    birth_date: date
    created_at: datetime
    updated_at: datetime


class AthleteCreate(AthleteBase):
    """Represents an athlete to be created."""
    pass


class AthleteUpdate(BaseModel):
    """Represents an athlete to be updated."""
    name: Optional[str] = None
    country: Optional[str] = None
    birth_date: Optional[date] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    sport: Optional[str] = None
    nick_name: Optional[str] = None
    bio: Optional[str] = None
