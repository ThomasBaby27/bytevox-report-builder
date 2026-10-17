import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="owner")
    reports = relationship("Report", back_populates="owner")

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    row_count = Column(Integer, default=0)
    columns_metadata = Column(Text, nullable=False)  # JSON-encoded column types & stats
    raw_data = Column(Text, nullable=False)          # JSON-encoded clean rows
    error_summary = Column(Text, nullable=True)     # JSON-encoded dropped/malformed rows
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="datasets")
    reports = relationship("Report", back_populates="dataset")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    dataset_id = Column(String, ForeignKey("datasets.id"), nullable=False)
    title = Column(String, nullable=False)
    global_filter = Column(Text, default="{}")       # JSON-encoded filters
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="reports")
    dataset = relationship("Dataset", back_populates="reports")
    blocks = relationship("ReportBlock", back_populates="report", cascade="all, delete-orphan")
    share_link = relationship("ShareLink", back_populates="report", uselist=False, cascade="all, delete-orphan")

class ReportBlock(Base):
    __tablename__ = "report_blocks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    order = Column(Integer, default=0)
    type = Column(String, nullable=False)            # metric, chart, table, text
    config = Column(Text, nullable=False)            # JSON-encoded configuration

    report = relationship("Report", back_populates="blocks")

class ShareLink(Base):
    __tablename__ = "share_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String, ForeignKey("reports.id"), unique=True, nullable=False)
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    is_revoked = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="share_link")