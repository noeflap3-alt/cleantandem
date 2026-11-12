"""CleanTandem development API v0.1 (NOT production ready).

Local prototype with separate organizations, Argon2 passwords, HTTP-only sessions,
CSRF and tenant-bound CRUD. Requires HTTPS deployment, audits, backups, policies
and monitoring before real customer information is entered.
"""
from __future__ import annotations

import hashlib
from html import escape as html_escape
import hmac
import os
import re
from pathlib import Path
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, create_engine, event, select, text as sql_text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from fastapi.staticfiles import StaticFiles

DATABASE_URL = os.environ.get("CT_DATABASE_URL") or os.environ.get("DATABASE_URL", "sqlite:///./cleantandem_dev.sqlite3")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
DEV_ALLOW_INSECURE = os.environ.get("CT_DEV_ALLOW_INSECURE") == "1"
PUBLIC_ORIGIN = os.environ.get("CT_PUBLIC_ORIGIN", "http://localhost:8000").rstrip("/")
REGISTRATION_CODE = os.environ.get("CT_REGISTRATION_CODE", "")
COOKIE_NAME = "ct_session"
SESSION_DAYS = 7
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

# SQLite is for local development only. Production should use a managed database,
# migrations, encrypted off-site backups, monitoring and a load-balanced environment.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {}, pool_pre_ping=True)
if DATABASE_URL.startswith("sqlite:"):
    @event.listens_for(engine, "connect")
    def _sqlite_constraints(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="owner")


class LoginSession(Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


Kind = Literal["clients", "sites", "quotes", "jobs"]


class Resource(Base):
    __tablename__ = "resources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (Index("ix_resources_tenant_kind", "organization_id", "kind"),)


class Identity(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Adresse email incorrecte")
        return value


class Register(Identity):
    organization_name: str = Field(min_length=2, max_length=120)
    invitation_code: str = Field(default="", max_length=128)


class NewRecord(BaseModel):
    payload: dict = Field(max_length=40)


class PatchRecord(NewRecord):
    pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Prevent accidental insecure publication without an explicitly configured TLS origin.
    if not DEV_ALLOW_INSECURE:
        if not PUBLIC_ORIGIN.startswith("https://"):
            raise RuntimeError("En production, CT_PUBLIC_ORIGIN doit être une URL HTTPS")
        if DATABASE_URL.startswith("sqlite:"):
            raise RuntimeError("En production, PostgreSQL est obligatoire (CT_DATABASE_URL ou DATABASE_URL)")
        if len(REGISTRATION_CODE) < 20:
            raise RuntimeError("En production, CT_REGISTRATION_CODE doit faire au moins 20 caractères")
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="CleanTandem API — prototype", version="0.1", lifespan=lifespan,
              docs_url="/dev/docs" if DEV_ALLOW_INSECURE else None,
              redoc_url=None)


def get_db():
    with SessionLocal() as db:
        yield db


DB = Annotated[Session, Depends(get_db)]


def sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def token_pair(db: Session, user: User, response: Response):
    token = secrets.token_urlsafe(36)
    csrf = secrets.token_urlsafe(30)
    db.add(LoginSession(token_hash=sha(token), user_id=user.id, csrf_hash=sha(csrf),
                        expires_at=utcnow() + timedelta(days=SESSION_DAYS)))
    db.commit()
    response.set_cookie(key=COOKIE_NAME, value=token, max_age=SESSION_DAYS*86400,
                        secure=not DEV_ALLOW_INSECURE, httponly=True, samesite="strict", path="/")
    return {"email": user.email, "organization_id": user.organization_id, "role": user.role, "csrf_token": csrf}


def signed_user(db: DB, ct_session: Annotated[str | None, Cookie()] = None):
    if not ct_session:
        raise HTTPException(401, "Connexion requise")
    db_session = db.get(LoginSession, sha(ct_session))
    if not db_session:
        raise HTTPException(401, "Session inconnue")
    expiry = db_session.expires_at.replace(tzinfo=timezone.utc) if db_session.expires_at.tzinfo is None else db_session.expires_at
    if expiry <= utcnow():
        db.delete(db_session);db.commit()
        raise HTTPException(401, "Session expirée")
    user = db.get(User, db_session.user_id)
    if not user:
        raise HTTPException(401, "Compte indisponible")
    return (user, db_session)


def require_write(request: Request, ident: Annotated[tuple[User, LoginSession], Depends(signed_user)],
                  csrf: Annotated[str | None, Header(alias="X-CSRF-Token")] = None):
    # CSRF token is returned to same-origin JS only after login, and never placed in a cookie.
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != PUBLIC_ORIGIN.rstrip("/"):
        raise HTTPException(403, "Origine non autorisée")
    if not csrf or not hmac.compare_digest(sha(csrf), ident[1].csrf_hash):
        raise HTTPException(403, "Jeton CSRF manquant ou invalide")
    return ident[0]


ReadUser = Annotated[tuple[User, LoginSession], Depends(signed_user)]
WriteUser = Annotated[User, Depends(require_write)]


@app.post("/auth/register", status_code=201)
def register(credentials: Register, response: Response, db: DB):
    if not DEV_ALLOW_INSECURE and not hmac.compare_digest(credentials.invitation_code, REGISTRATION_CODE):
        raise HTTPException(403, "Code d’invitation requis ou incorrect")
    if db.scalar(select(User).where(User.email == credentials.email)):
        raise HTTPException(409, "Adresse déjà utilisée")
    org = Organization(id=str(uuid.uuid4()), name=credentials.organization_name.strip())
    user = User(id=str(uuid.uuid4()), organization_id=org.id, email=credentials.email,
                password_hash=ph.hash(credentials.password), role="owner")
    db.add_all((org, user))
    db.commit()
    return token_pair(db,user,response)


@app.post("/auth/login")
def login(credentials: Identity, response: Response, db: DB):
    user = db.scalar(select(User).where(User.email == credentials.email))
    if not user:
        raise HTTPException(401, "Identifiants incorrects")
    try:
        ph.verify(user.password_hash, credentials.password)
    except (VerifyMismatchError, VerificationError):
        raise HTTPException(401, "Identifiants incorrects") from None
    return token_pair(db,user,response)


@app.get("/auth/me")
def me(ident: ReadUser):
    user, session = ident
    # Re-issue CSRF on login only; an active SPA should retain it in memory.
    return {"email": user.email, "organization_id": user.organization_id, "role":user.role}


@app.post("/auth/logout", status_code=204)
def logout(response: Response, user: WriteUser, db: DB, ct_session: Annotated[str | None, Cookie()] = None):
    if ct_session:
        session = db.get(LoginSession, sha(ct_session))
        if session and session.user_id == user.id:
            db.delete(session);db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return Response(status_code=204, headers={"Set-Cookie":f"{COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"})


def scoped_record(db: Session, org: str, kind: str, resource_id: str):
    rec = db.scalar(select(Resource).where(Resource.id == resource_id,Resource.organization_id == org,Resource.kind == kind))
    if not rec:
        raise HTTPException(404, "Élément introuvable")
    return rec


def validate_ref(db: Session, org: str, kind: str, rid: str | None):
    if rid:
        scoped_record(db,org,kind,rid)


def sanitize_payload(db: Session, org: str, kind: str, obj: dict):
    """Minimal fail-closed validation, sufficient for a prototype, not a public API contract."""
    if not isinstance(obj,dict):
        raise HTTPException(422,"Objet incorrect")
    if len(str(obj)) > 30000:
        raise HTTPException(413,"Données trop volumineuses")
    if not isinstance(obj.get("name" if kind in ("clients","sites") else "title"),str):
        raise HTTPException(422,"Nom ou titre obligatoire")
    required_field = "name" if kind in ("clients","sites") else "title"
    if not 1 <= len(obj[required_field].strip()) <= 140:
        raise HTTPException(422,"Nom ou titre invalide")
    if kind != "clients":
        validate_ref(db,org,"clients",obj.get("client_id"))
        if not obj.get("client_id"):
            raise HTTPException(422,"Client requis")
    if kind in ("jobs","quotes"):
        validate_ref(db,org,"sites",obj.get("site_id"))
        if obj.get("site_id") and scoped_record(db,org,"sites",obj["site_id"]).payload.get("client_id") != obj.get("client_id"):
            raise HTTPException(422,"Le site doit appartenir au client sélectionné")
    if kind == "jobs":
        if obj.get("status", "prévue") not in ("prévue", "réalisée", "annulée"):
            raise HTTPException(422,"Statut d'intervention incorrect")
        if not isinstance(obj.get("date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", obj["date"]):
            raise HTTPException(422,"Date d'intervention requise")
        for k in ("duration_minutes", "labor_rate_cents", "supplies_cents", "travel_cents", "revenue_cents"):
            n = obj.get(k, 0)
            if isinstance(n, bool) or not isinstance(n, int) or n < 0 or n > 100000000:
                raise HTTPException(422, "Coût ou durée invalide")
    if kind == "quotes":
        if obj.get("status", "brouillon") not in ("brouillon", "envoyé", "accepté", "refusé"):
            raise HTTPException(422, "Statut de devis incorrect")
        lines = obj.get("lines",[])
        if not isinstance(lines,list) or not 1 <= len(lines) <= 50:
            raise HTTPException(422,"Entre 1 et 50 prestations sont nécessaires")
        for line in lines:
            if not isinstance(line,dict) or not isinstance(line.get("description"),str) or not line["description"].strip():
                raise HTTPException(422,"Ligne de devis incorrecte")
            if not isinstance(line.get("quantity"),int) or line["quantity"] <= 0 or line["quantity"] > 10000:
                raise HTTPException(422,"Quantité incorrecte")
            if not isinstance(line.get("unit_price_cents"),int) or not 0 <= line["unit_price_cents"] <= 100000000:
                raise HTTPException(422,"Prix en centimes incorrect")
    return obj


@app.get("/auth/csrf")
def csrf_for_session(ident: ReadUser, db: DB):
    # Restores anti-CSRF protection after a page reload without exposing the cookie.
    csrf = secrets.token_urlsafe(30)
    ident[1].csrf_hash = sha(csrf)
    db.commit()
    return {"csrf_token": csrf}


@app.middleware("http")
async def safe_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
    if request.url.path.startswith(("/auth", "/api")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/api/export")
def export_demo_data(ident: ReadUser, db: DB):
    """Owner-scoped JSON export for a local development workspace."""
    user = ident[0]
    org = db.get(Organization, user.organization_id)
    all_records = db.scalars(select(Resource).where(Resource.organization_id == user.organization_id)).all()
    snapshot = {
        "format": "cleantandem-local-demo",
        "version": 1,
        "exported_at": utcnow().isoformat(),
        "organization_name": org.name if org else "",
        "resources": {kind: [{"id": rec.id, **rec.payload} for rec in all_records if rec.kind == kind]
                      for kind in ("clients", "sites", "quotes", "jobs")},
        "warning": "Données de démonstration uniquement. Archive non chiffrée. Ne pas y insérer d'informations réelles.",
    }
    return JSONResponse(snapshot, headers={
        "Cache-Control": "private, no-store",
        "Content-Disposition": 'attachment; filename="cleantandem-export-demo.json"',
    })


def display_amount(cents: int) -> str:
    return f"{int(cents) / 100:,.2f}".replace(",", " ").replace(".", ",") + " €"


@app.get("/api/quotes/{resource_id}/print", response_class=HTMLResponse)
def print_quote(resource_id: str, ident: ReadUser, db: DB):
    """Printable non-contractual estimate; tenant-scoped, no invoicing claims."""
    user = ident[0]
    quote = scoped_record(db, user.organization_id, "quotes", resource_id)
    payload = quote.payload
    client = scoped_record(db, user.organization_id, "clients", payload.get("client_id", ""))
    site_id = payload.get("site_id")
    site = scoped_record(db, user.organization_id, "sites", site_id) if site_id else None
    def h(value):
        return html_escape(str(value or ""), quote=True)
    rows = []
    total = 0
    for line in payload.get("lines", []):
        q = int(line["quantity"])
        price = int(line["unit_price_cents"])
        subtotal = q * price
        total += subtotal
        rows.append(f"<tr><td>{h(line['description'])}</td><td>{q}</td><td>{display_amount(price)}</td><td>{display_amount(subtotal)}</td></tr>")
    html = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Devis fictif — CleanTandem</title><style>body{{font-family:Arial,sans-serif;max-width:850px;margin:40px auto;padding:0 20px;color:#1a3131}}h1{{font-size:32px}}.warning{{background:#fff1d6;border:1px solid #c58d34;padding:16px;margin-bottom:24px}}table{{border-collapse:collapse;width:100%;margin:30px 0}}th,td{{border-bottom:1px solid #ddd;padding:12px;text-align:left}}th{{background:#eef7f5}}.total{{text-align:right;font-size:24px;font-weight:bold}}.subtle{{color:#516368}}@media print{{body{{margin:0}}.warning{{border:2px solid black}}}}</style></head><body>
    <p class="warning"><strong>DOCUMENT FICTIF — NON CONTRACTUEL</strong><br>Prototype local CleanTandem : ne pas transmettre comme devis professionnel ni facture.</p>
    <h1>Brouillon de devis</h1><p><strong>{h(payload['title'])}</strong></p><p class="subtle">Statut : {h(payload.get('status','brouillon'))}</p>
    <p><strong>Client fictif :</strong> {h(client.payload['name'])}<br><strong>Site :</strong> {h(site.payload['name']) if site else '—'}</p>
    <table><thead><tr><th>Prestation</th><th>Qté</th><th>Prix HT</th><th>Total HT</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <p class="total">Total prévisionnel HT : {display_amount(total)}</p>
    <p class="subtle">TVA, numérotation réglementaire, conditions de vente et mentions de l'éditeur : non intégrées à cette démonstration.</p></body></html>'''
    return HTMLResponse(html, headers={"Cache-Control": "private, no-store"})


@app.get("/api/{kind}")
def records(kind: Kind, ident: ReadUser, db: DB):
    org = ident[0].organization_id
    result = db.scalars(select(Resource).where(Resource.organization_id==org,Resource.kind==kind).order_by(Resource.created_at.desc())).all()
    return [{"id":r.id,**r.payload} for r in result]


@app.post("/api/{kind}",status_code=201)
def create_record(kind: Kind, item: NewRecord, user: WriteUser, db: DB):
    obj = sanitize_payload(db,user.organization_id,kind,item.payload)
    rec = Resource(id=str(uuid.uuid4()), organization_id=user.organization_id,kind=kind,payload=obj)
    db.add(rec); db.commit()
    return {"id":rec.id,**rec.payload}


@app.patch("/api/{kind}/{resource_id}")
def update_record(kind: Kind,resource_id: str,item: PatchRecord,user: WriteUser,db: DB):
    rec=scoped_record(db,user.organization_id,kind,resource_id)
    merged={**rec.payload,**item.payload}
    rec.payload=sanitize_payload(db,user.organization_id,kind,merged)
    rec.updated_at=utcnow()
    db.commit()
    return {"id":rec.id,**rec.payload}


@app.delete("/api/{kind}/{resource_id}",status_code=204)
def delete_record(kind: Kind,resource_id: str,user: WriteUser,db: DB):
    rec=scoped_record(db,user.organization_id,kind,resource_id)
    if kind in ("clients","sites"):
        dependents=db.scalars(select(Resource).where(Resource.organization_id==user.organization_id)).all()
        field="client_id" if kind == "clients" else "site_id"
        if any(r.id != rec.id and r.payload.get(field)==resource_id for r in dependents):
            raise HTTPException(409,"Supprimez les éléments dépendants avant")
    db.delete(rec);db.commit()
    return Response(status_code=204)


@app.get("/health")
def health(db: DB):
    db.execute(sql_text("SELECT 1"))
    return {"status":"ok","environment":"local-development" if DEV_ALLOW_INSECURE else "pilot-staging-demo-only"}


# Same-origin frontend for a demo/staging service only; NOT approved for real customer data.
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")