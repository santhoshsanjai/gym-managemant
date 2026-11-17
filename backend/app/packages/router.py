from fastapi import APIRouter
from sqlalchemy import func, select

from app.auth.deps import DB, AdminUser, CurrentUser
from app.common import audit
from app.common.errors import conflict, not_found
from app.packages.models import Package
from app.packages.schemas import PackageCreate, PackageOut, PackagePublic, PackageUpdate

router = APIRouter(prefix="/packages", tags=["packages"])


def _get(db, package_id: int) -> Package:
    p = db.get(Package, package_id)
    if p is None:
        raise not_found("Package")
    return p


def _name_taken(db, name: str, exclude: int | None = None) -> bool:
    q = select(Package.id).where(func.lower(Package.name) == name.strip().lower())
    if exclude:
        q = q.where(Package.id != exclude)
    return db.scalar(q) is not None


@router.get("/available", response_model=list[PackagePublic])
def available_packages(db: DB, _: CurrentUser):
    """Active packages, visible to any signed-in user (members included)."""
    return db.scalars(select(Package).where(Package.is_active.is_(True)).order_by(Package.price)).all()


@router.get("", response_model=list[PackageOut])
def list_packages(db: DB, _: AdminUser, include_inactive: bool = True):
    stmt = select(Package).order_by(Package.is_active.desc(), Package.name)
    if not include_inactive:
        stmt = stmt.where(Package.is_active.is_(True))
    return db.scalars(stmt).all()


@router.post("", response_model=PackageOut, status_code=201)
def create_package(body: PackageCreate, db: DB, admin: AdminUser):
    if _name_taken(db, body.name):
        raise conflict("A package with this name already exists")
    p = Package(**body.model_dump())
    db.add(p)
    db.flush()
    audit.record(db, admin.id, "create", "package", p.id, name=p.name, price=p.price)
    db.commit()
    return p


@router.get("/{package_id}", response_model=PackageOut)
def get_package(package_id: int, db: DB, _: AdminUser):
    return _get(db, package_id)


@router.patch("/{package_id}", response_model=PackageOut)
def update_package(package_id: int, body: PackageUpdate, db: DB, admin: AdminUser):
    """Edits never affect existing subscriptions, which keep their own snapshot.
    Deactivating prevents new assignments only."""
    p = _get(db, package_id)
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "description"}
    if "name" in changes and _name_taken(db, changes["name"], exclude=p.id):
        raise conflict("A package with this name already exists")
    for k, v in changes.items():
        setattr(p, k, v)
    audit.record(db, admin.id, "update", "package", p.id, changes=changes)
    db.commit()
    return p
