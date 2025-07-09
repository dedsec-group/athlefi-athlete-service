"""Athlete API router module."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SessionDep
from app.models import Athlete, AthleteCreate, AthletePublic, AthleteUpdate


router = APIRouter(
    prefix="/athletes",
    tags=["athletes"],
)


@router.post("/")
async def create_athlete(athlete: AthleteCreate, session: SessionDep):
    """Create a new athlete."""
    db_athlete = Athlete(**athlete.model_dump())
    session.add(db_athlete)
    await session.commit()
    await session.refresh(db_athlete)
    return db_athlete


@router.get("/", response_model=list[AthletePublic])
async def get_athletes(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    """Get a list of athletes."""
    statement = select(Athlete).offset(offset).limit(limit)
    result = await session.execute(statement)
    athletes = result.scalars().all()
    return athletes


@router.get("/{athlete_id}", response_model=AthletePublic)
async def get_athlete(athlete_id: int, session: SessionDep):
    """Get an athlete by ID."""
    statement = select(Athlete).where(Athlete.id == athlete_id)
    result = await session.execute(statement)
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


@router.patch("/{athlete_id}", response_model=AthletePublic)
async def update_athlete(athlete_id: int, athlete: AthleteUpdate, session: SessionDep):
    """Update an athlete."""
    statement = select(Athlete).where(Athlete.id == athlete_id)
    result = await session.execute(statement)
    db_athlete = result.scalar_one_or_none()
    if not db_athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    athlete_data = athlete.model_dump(exclude_unset=True)
    for key, value in athlete_data.items():
        setattr(db_athlete, key, value)

    session.add(db_athlete)
    await session.commit()
    await session.refresh(db_athlete)
    return db_athlete


@router.delete("/{athlete_id}")
async def delete_athlete(athlete_id: int, session: SessionDep):
    """Delete an athlete."""
    statement = select(Athlete).where(Athlete.id == athlete_id)
    result = await session.execute(statement)
    athlete = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    await session.delete(athlete)
    await session.commit()
    return {"message": "Athlete deleted"}
