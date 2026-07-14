from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from . import models, schemas


def get_or_create_hcp(db: Session, name: str) -> models.HCP:
    hcp = db.scalar(select(models.HCP).where(models.HCP.name.ilike(name.strip())))
    if hcp:
        return hcp
    hcp = models.HCP(name=name.strip())
    db.add(hcp)
    db.flush()
    return hcp


def create_interaction(db: Session, data: schemas.InteractionCreate) -> models.Interaction:
    hcp = get_or_create_hcp(db, data.hcp_name)
    record = models.Interaction(hcp_id=hcp.id, **data.model_dump(exclude={"hcp_name", "follow_up_due_at"}))
    db.add(record)
    db.flush()
    if data.follow_up_action and data.follow_up_due_at:
        db.add(models.FollowUp(hcp_id=hcp.id, interaction_id=record.id, due_at=data.follow_up_due_at, action=data.follow_up_action))
    db.commit()
    return get_interaction(db, record.id)


def get_interaction(db: Session, interaction_id: int) -> models.Interaction | None:
    return db.scalar(select(models.Interaction).options(joinedload(models.Interaction.hcp)).where(models.Interaction.id == interaction_id))


def update_interaction(db: Session, record: models.Interaction, data: schemas.InteractionUpdate) -> models.Interaction:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    db.commit()
    return get_interaction(db, record.id)


def list_interactions(db: Session, query: str | None = None, limit: int = 30) -> list[models.Interaction]:
    statement = select(models.Interaction).options(joinedload(models.Interaction.hcp)).order_by(models.Interaction.occurred_at.desc()).limit(limit)
    if query:
        statement = statement.join(models.HCP).where((models.HCP.name.ilike(f"%{query}%")) | (models.Interaction.notes.ilike(f"%{query}%")))
    return list(db.scalars(statement).unique())


def record_to_dict(record: models.Interaction) -> dict:
    return {
        "id": record.id, "hcp_name": record.hcp.name, "occurred_at": record.occurred_at.isoformat(),
        "interaction_type": record.interaction_type, "products": record.products, "notes": record.notes,
        "samples_distributed": record.samples_distributed, "sentiment": record.sentiment,
        "follow_up_action": record.follow_up_action, "compliance_flags": record.compliance_flags,
    }
