from sqlalchemy import create_engine, Column, String, Integer, UUID, DateTime, ARRAY, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ProcessingRequest(Base):
    __tablename__ = "processing_requests"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    webhook_url = Column(String, nullable=True)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    request_id = Column(UUID(as_uuid=True), ForeignKey('processing_requests.id'))
    serial_number = Column(Integer)
    product_name = Column(String)
    input_urls = Column(ARRAY(Text))
    output_urls = Column(ARRAY(Text))

Base.metadata.create_all(bind=engine)