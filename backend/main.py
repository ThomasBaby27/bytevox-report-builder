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
from engine import parse_and_profile_csv, compute_block_calculation, MAX_FILE_SIZE_BYTES
from datetime import datetime, timedelta
import uuid
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
    
class BlockSchema(BaseModel):
    id: Optional[str] = None
    type: str
    order: int
    config: Dict[str, Any]

class ReportCreateSchema(BaseModel):
    dataset_id: str
    title: str
    global_filter: Optional[Dict[str, Any]] = {}
    blocks: List[BlockSchema] = []

@app.post("/api/reports")
def create_or_update_report(
    payload: ReportCreateSchema,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Verify dataset belongs to current user
    dataset = db.query(models.Dataset).filter(
        models.Dataset.id == payload.dataset_id,
        models.Dataset.user_id == current_user.id
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found or access denied")

    report = models.Report(
        user_id=current_user.id,
        dataset_id=dataset.id,
        title=payload.title,
        global_filter=json.dumps(payload.global_filter)
    )
    db.add(report)
    db.flush()

    for b in payload.blocks:
        block = models.ReportBlock(
            report_id=report.id,
            order=b.order,
            type=b.type,
            config=json.dumps(b.config)
        )
        db.add(block)

    db.commit()
    db.refresh(report)
    return {"report_id": report.id, "message": "Report created successfully"}

@app.get("/api/reports/{report_id}")
def get_report(
    report_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(models.Report).filter(
        models.Report.id == report_id,
        models.Report.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    raw_data = json.loads(report.dataset.raw_data)
    global_filter = json.loads(report.global_filter) if report.global_filter else {}

    computed_blocks = []
    for b in sorted(report.blocks, key=lambda x: x.order):
        config = json.loads(b.config)
        calc_result = compute_block_calculation(raw_data, b.type, config, global_filter)
        computed_blocks.append({
            "id": b.id,
            "type": b.type,
            "order": b.order,
            "config": config,
            "result": calc_result
        })

    return {
        "id": report.id,
        "title": report.title,
        "dataset_id": report.dataset_id,
        "dataset_name": report.dataset.filename,
        "global_filter": global_filter,
        "blocks": computed_blocks
    }
    
class ShareCreateSchema(BaseModel):
    expires_in_hours: Optional[int] = 24

@app.post("/api/reports/{report_id}/share")
def create_share_link(
    report_id: str,
    payload: ShareCreateSchema,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Verify the report belongs to the current user
    report = db.query(models.Report).filter(
        models.Report.id == report_id,
        models.Report.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # If share link already exists, update or replace it
    existing_link = db.query(models.ShareLink).filter(models.ShareLink.report_id == report.id).first()
    expires_at = datetime.utcnow() + timedelta(hours=payload.expires_in_hours) if payload.expires_in_hours else None

    if existing_link:
        existing_link.token = str(uuid.uuid4())
        existing_link.is_revoked = False
        existing_link.expires_at = expires_at
        db.commit()
        db.refresh(existing_link)
        return {"token": existing_link.token, "expires_at": existing_link.expires_at}

    share = models.ShareLink(
        report_id=report.id,
        token=str(uuid.uuid4()),
        is_revoked=False,
        expires_at=expires_at
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {"token": share.token, "expires_at": share.expires_at}

@app.delete("/api/reports/{report_id}/share")
def revoke_share_link(
    report_id: str,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(models.Report).filter(
        models.Report.id == report_id,
        models.Report.user_id == current_user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    share = db.query(models.ShareLink).filter(models.ShareLink.report_id == report.id).first()
    if not share:
        raise HTTPException(status_code=404, detail="No active share link found")

    share.is_revoked = True
    db.commit()
    return {"message": "Share link revoked successfully"}

@app.get("/api/shared/{token}")
def get_shared_report(token: str, db: Session = Depends(get_db)):
    share = db.query(models.ShareLink).filter(models.ShareLink.token == token).first()
    
    # Strictly reject revoked links
    if not share or share.is_revoked:
        raise HTTPException(status_code=404, detail="This shared report does not exist or has been revoked.")

    # Strictly reject expired links
    if share.expires_at and datetime.utcnow() > share.expires_at:
        raise HTTPException(status_code=410, detail="This shared link has expired.")

    report = share.report
    raw_data = json.loads(report.dataset.raw_data)
    global_filter = json.loads(report.global_filter) if report.global_filter else {}

    # Deliver only computed results; never expose raw_data or raw CSV
    computed_blocks = []
    for b in sorted(report.blocks, key=lambda x: x.order):
        config = json.loads(b.config)
        calc_result = compute_block_calculation(raw_data, b.type, config, global_filter)
        computed_blocks.append({
            "id": b.id,
            "type": b.type,
            "order": b.order,
            "config": config,
            "result": calc_result
        })

    return {
        "title": report.title,
        "dataset_name": report.dataset.filename,
        "global_filter": global_filter,
        "blocks": computed_blocks,
        "is_shared": True
    }
    