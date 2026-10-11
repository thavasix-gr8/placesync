from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .auth import create_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .models import User
from .routes_applications import router as applications_router
from .routes_drives import router as drives_router
from .schemas import SignupRequest, UserOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="PlaceSync API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(drives_router)
app.include_router(applications_router)
