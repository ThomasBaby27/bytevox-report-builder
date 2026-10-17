from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models
import auth

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ByteVox Report Builder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserAuthSchema(BaseModel):
    email: EmailStr
    password: str

@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(user_data: UserAuthSchema, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = auth.get_password_hash(user_data.password)
    user = models.User(email=user_data.email, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "email": user.email}

@app.post("/api/auth/login")
def login(user_data: UserAuthSchema, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    token = auth.create_access_token({"sub": user.email})
    return {"access_token": token, "token_type": "bearer", "email": user.email}

@app.get("/api/auth/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {"id": current_user.id, "email": current_user.email}