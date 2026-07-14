from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=schemas.InteractionRead, status_code=201)
def create_interaction(payload: schemas.InteractionCreate, db: Session = Depends(get_db)):
    return crud.create_interaction(db, payload)


@router.put("/{interaction_id}", response_model=schemas.InteractionRead)
def edit_interaction(interaction_id: int, payload: schemas.InteractionUpdate, db: Session = Depends(get_db)):
    record = crud.get_interaction(db, interaction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return crud.update_interaction(db, record, payload)


@router.get("", response_model=list[schemas.InteractionRead])
def get_interactions(q: str | None = Query(default=None, max_length=180), db: Session = Depends(get_db)):
    return crud.list_interactions(db, q)
