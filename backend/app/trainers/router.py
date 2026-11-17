from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.auth.deps import DB, AdminUser, require_admin
from app.common import audit
from app.common.errors import conflict, not_found
from app.common.pagination import Page, PageParams, paginate
from app.members.models import Member
from app.trainers.models import Trainer, TrainerStatus
from app.trainers.schemas import TrainerCreate, TrainerOut, TrainerUpdate

router = APIRouter(prefix="/trainers", tags=["trainers"], dependencies=[Depends(require_admin)])


def _get(db, trainer_id: int) -> Trainer:
    t = db.get(Trainer, trainer_id)
    if t is None:
        raise not_found("Trainer")
    return t


def _with_counts(db, trainers: list[Trainer]) -> list[TrainerOut]:
    ids = [t.id for t in trainers]
    counts = (
        dict(
            db.execute(
                select(Member.trainer_id, func.count()).where(Member.trainer_id.in_(ids)).group_by(Member.trainer_id)
            ).all()
        )
        if ids
        else {}
    )
    out = []
    for t in trainers:
        o = TrainerOut.model_validate(t)
        o.assigned_members = counts.get(t.id, 0)
        out.append(o)
    return out


def _mobile_taken(db, mobile: str, exclude: int | None = None) -> bool:
    q = select(Trainer.id).where(Trainer.mobile == mobile)
    if exclude:
        q = q.where(Trainer.id != exclude)
    return db.scalar(q) is not None


@router.get("", response_model=Page[TrainerOut])
def list_trainers(
    db: DB,
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=100),
    status: TrainerStatus | None = None,
):
    stmt = select(Trainer)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(or_(func.lower(Trainer.full_name).like(term), Trainer.mobile.like(term)))
    if status:
        stmt = stmt.where(Trainer.status == status)
    page = paginate(db, stmt.order_by(Trainer.full_name), params)
    page["items"] = _with_counts(db, page["items"])
    return page


@router.post("", response_model=TrainerOut, status_code=201)
def create_trainer(body: TrainerCreate, db: DB, admin: AdminUser):
    if _mobile_taken(db, body.mobile):
        raise conflict("A trainer with this mobile number already exists")
    t = Trainer(**body.model_dump())
    db.add(t)
    db.flush()
    audit.record(db, admin.id, "create", "trainer", t.id, full_name=t.full_name)
    db.commit()
    return _with_counts(db, [t])[0]


@router.get("/{trainer_id}", response_model=TrainerOut)
def get_trainer(trainer_id: int, db: DB):
    return _with_counts(db, [_get(db, trainer_id)])[0]


@router.patch("/{trainer_id}", response_model=TrainerOut)
def update_trainer(trainer_id: int, body: TrainerUpdate, db: DB, admin: AdminUser):
    t = _get(db, trainer_id)
    changes = body.model_dump(exclude_unset=True)
    if changes.get("mobile") and _mobile_taken(db, changes["mobile"], exclude=t.id):
        raise conflict("A trainer with this mobile number already exists")
    for k, v in changes.items():
        if k in ("full_name", "mobile", "status") and v is None:
            continue
        setattr(t, k, v)
    audit.record(db, admin.id, "update", "trainer", t.id, fields=sorted(changes))
    db.commit()
    return _with_counts(db, [t])[0]


@router.delete("/{trainer_id}", status_code=204)
def delete_trainer(trainer_id: int, db: DB, admin: AdminUser):
    """Hard delete is only allowed when no member is assigned; otherwise
    deactivate the trainer so member history stays intact."""
    t = _get(db, trainer_id)
    if db.scalar(select(func.count()).select_from(Member).where(Member.trainer_id == t.id)):
        raise conflict("Trainer has assigned members. Reassign them or deactivate the trainer instead.")
    audit.record(db, admin.id, "delete", "trainer", t.id, full_name=t.full_name)
    db.delete(t)
    db.commit()
