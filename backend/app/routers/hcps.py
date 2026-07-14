from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/hcps", tags=["hcps"])


@router.get("", response_model=list[schemas.HCPRead])
def get_hcps(db: Session = Depends(get_db)):
    return list(db.scalars(select(models.HCP).order_by(models.HCP.name)))
