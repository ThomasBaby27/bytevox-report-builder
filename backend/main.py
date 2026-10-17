from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models
import auth
from fastapi import UploadFile, File
import json
from engine import parse_and_profile_csv, MAX_FILE_SIZE_BYTES

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

@app.post("/api/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Only .csv files are supported.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds the 10 MB limit.")

    try:
        profile, valid_rows, unparsed_rows = parse_and_profile_csv(file_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    dataset = models.Dataset(
        user_id=current_user.id,
        filename=file.filename,
        row_count=profile["valid_rows_count"],
        columns_metadata=json.dumps(profile["columns"]),
        raw_data=json.dumps(valid_rows),
        error_summary=json.dumps(unparsed_rows)
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {
        "dataset_id": dataset.id,
        "profile": profile
    }

@app.get("/api/datasets")
def list_datasets(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    datasets = db.query(models.Dataset).filter(models.Dataset.user_id == current_user.id).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "row_count": d.row_count,
            "columns": json.loads(d.columns_metadata),
            "created_at": d.created_at
        }
        for d in datasets
    ]

@app.get("/api/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == dataset_id,
        models.Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "id": dataset.id,
        "filename": dataset.filename,
        "row_count": dataset.row_count,
        "columns": json.loads(dataset.columns_metadata),
        "unparsed_rows": json.loads(dataset.error_summary) if dataset.error_summary else [],
        "preview": json.loads(dataset.raw_data)[:10]
    }