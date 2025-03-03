from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import csv
from io import StringIO, BytesIO
from concurrent.futures import ProcessPoolExecutor
import asyncio
from .database import SessionLocal, ProcessingRequest, Product
from .schemas import CSVUploadResponse, StatusResponse
from .processors import process_csv
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()
app.mount("/processed_images", StaticFiles(directory=os.getenv("PROCESSED_IMAGES_DIR")), name="processed_images")

executor = ProcessPoolExecutor(max_workers=4)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload", response_model=CSVUploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    webhook_url: str = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format.")
    
    content = (await file.read()).decode()
    csv_reader = csv.DictReader(StringIO(content))
    if not {'S. No.', 'Product Name', 'Input Image Urls'}.issubset(csv_reader.fieldnames):
        raise HTTPException(status_code=400, detail="Invalid CSV headers.")
    
    request_id = uuid.uuid4()
    db_request = ProcessingRequest(id=request_id, webhook_url=webhook_url)
    db.add(db_request)
    db.commit()
    
    # Use the current running loop and log task submission
    loop = asyncio.get_running_loop()
    logger.info(f"Submitting task for request_id: {request_id}")
    loop.run_in_executor(executor, process_csv, str(request_id), content)
    
    return {"request_id": request_id}

@app.get("/status/{request_id}", response_model=StatusResponse)
def get_status(request_id: uuid.UUID, db: Session = Depends(get_db)):
    request = db.query(ProcessingRequest).get(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Request not found.")
    return {"status": request.status}

@app.get("/download/{request_id}")
def download_output_csv(request_id: uuid.UUID, db: Session = Depends(get_db)):
    # Query products for the given request_id
    products = db.query(Product).filter(Product.request_id == request_id).all()
    if not products:
        raise HTTPException(status_code=404, detail="No products found for the given request_id.")
    
    # Create a CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(["S. No.", "Product Name", "Input Image Urls", "Output Image Urls"])
    
    # Write data rows
    for product in products:
        input_urls = ",".join(product.input_urls) if product.input_urls else ""
        output_urls = ",".join(product.output_urls) if product.output_urls else ""
        writer.writerow([product.serial_number, product.product_name, input_urls, output_urls])
    
    output.seek(0)
    csv_bytes = BytesIO(output.getvalue().encode("utf-8"))
    
    headers = {
        "Content-Disposition": f"attachment; filename=output_{request_id}.csv"
    }
    return StreamingResponse(csv_bytes, media_type="text/csv", headers=headers)

@app.on_event("shutdown")
def shutdown_executor():
    executor.shutdown()
