from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .auth import create_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .migrations import upgrade_microsoft_identity, upgrade_resume_feature
from .models import MicrosoftIdentity, User
from .microsoft_auth import (
    check_microsoft_nonce,
    issue_microsoft_nonce,
    microsoft_settings,
    verify_microsoft_id_token,
)
from .routes_applications import router as applications_router
from .routes_drives import router as drives_router
from .routes_resumes import router as resumes_router
from .schemas import SignupRequest, UserOut
from .schemas_auth import MicrosoftTokenRequest


def ensure_schema():
    upgrade_microsoft_identity(engine.url.database)
    upgrade_resume_feature(engine.url.database)
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app):
    ensure_schema()
    yield


app = FastAPI(title="PlaceSync API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Resumes-Skipped"],
)


@app.get("/")
def root():
    return {"message": "PlaceSync API is running"}


@app.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
    if db.query(User).filter(User.register_number == data.register_number).first():
        raise HTTPException(status_code=400, detail="Register number is already registered")

    student = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="student",
        register_number=data.register_number,
        department=data.department,
        batch=data.batch,
        cgpa=data.cgpa,
        arrears=data.arrears,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "role": user.role}


@app.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/auth/microsoft/nonce")
def microsoft_nonce(db: Session = Depends(get_db)):
    microsoft_settings()
    return {"nonce": issue_microsoft_nonce(db)}


@app.post("/auth/microsoft/login")
def microsoft_login(data: MicrosoftTokenRequest, db: Session = Depends(get_db)):
    claims = verify_microsoft_id_token(data.id_token)
    check_microsoft_nonce(claims, db, consume=False)
    identity = db.query(MicrosoftIdentity).filter(
        MicrosoftIdentity.tenant_id == claims["tid"].casefold(),
        MicrosoftIdentity.object_id == claims["oid"],
    ).first()
    if identity is None:
        raise HTTPException(
            status_code=409,
            detail="Microsoft account is not linked. Sign in with your PlaceSync password to link it.",
        )
    user = identity.user
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Microsoft sign-in is available to students only.")
    check_microsoft_nonce(claims, db, consume=True)
    return {"access_token": create_token(user), "token_type": "bearer", "role": "student"}


@app.post("/auth/microsoft/link")
def microsoft_link(
    data: MicrosoftTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    claims = verify_microsoft_id_token(data.id_token)
    check_microsoft_nonce(claims, db, consume=False)
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only student accounts can link Microsoft sign-in.")

    microsoft_email = claims.get("email")
    if not isinstance(microsoft_email, str) or not microsoft_email.strip():
        raise HTTPException(
            status_code=400,
            detail="Microsoft did not provide an email. Ask your college administrator to enable the email claim.",
        )
    if claims.get("email_verified") is False:
        raise HTTPException(status_code=400, detail="Microsoft reports this email address as unverified.")
    if microsoft_email.strip().casefold() != current_user.email.strip().casefold():
        raise HTTPException(
            status_code=400,
            detail="Microsoft email must match your PlaceSync student email before linking.",
        )

    identity = db.query(MicrosoftIdentity).filter(
        MicrosoftIdentity.tenant_id == claims["tid"].casefold(),
        MicrosoftIdentity.object_id == claims["oid"],
    ).first()
    if identity and identity.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="This Microsoft account is already linked to another account.")
    if current_user.microsoft_identity and current_user.microsoft_identity.object_id != claims["oid"]:
        raise HTTPException(status_code=409, detail="This PlaceSync account already has a Microsoft account linked.")
    check_microsoft_nonce(claims, db, consume=True)
    if identity is None:
        db.add(MicrosoftIdentity(
            tenant_id=claims["tid"].casefold(), object_id=claims["oid"], user_id=current_user.id
        ))
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="This Microsoft account was linked elsewhere. Please sign in again.") from exc
    return {
        "access_token": create_token(current_user),
        "token_type": "bearer",
        "role": "student",
    }


app.include_router(drives_router)
app.include_router(applications_router)
app.include_router(resumes_router)
