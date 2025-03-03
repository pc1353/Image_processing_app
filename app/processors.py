import csv
from io import StringIO
import uuid
import os
import requests
from PIL import Image
import io
from sqlalchemy.orm import sessionmaker
from .database import engine, ProcessingRequest, Product
from .utils import compress_and_save_image
import logging

logger = logging.getLogger(__name__)

def process_csv(request_id: str, content: str):
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    request = None
    try:
        logger.info(f"Starting processing for request_id: {request_id}")
        
        # Verify request exists and set status to 'processing'
        request = db.query(ProcessingRequest).get(uuid.UUID(request_id))
        if not request:
            logger.error(f"Request not found for request_id: {request_id}")
            return
        request.status = 'processing'
        db.commit()
        
        csv_reader = csv.DictReader(StringIO(content))
        products = []
        processed_images_dir = os.getenv("PROCESSED_IMAGES_DIR", "processed_images")
        
        for row in csv_reader:
            serial_number = int(row['S. No.'])
            product_name = row['Product Name']
            input_urls = row['Input Image Urls'].split(',')
            output_urls = []
            
            for url in input_urls:
                try:
                    response = requests.get(url.strip(), timeout=10)
                    response.raise_for_status()
                    image = Image.open(io.BytesIO(response.content))
                    
                    output_filename = f"{uuid.uuid4()}.jpg"
                    output_dir = os.path.join(processed_images_dir, request_id, product_name)
                    os.makedirs(output_dir, exist_ok=True)
                    output_path = os.path.join(output_dir, output_filename)
                    
                    compress_and_save_image(image, output_path)
                    output_url = f"/processed_images/{request_id}/{product_name}/{output_filename}"
                    output_urls.append(output_url)
                except Exception as e:
                    logger.warning(f"Failed to process image URL {url}: {str(e)}")
                    continue
            
            product = Product(
                request_id=uuid.UUID(request_id),
                serial_number=serial_number,
                product_name=product_name,
                input_urls=input_urls,
                output_urls=output_urls
            )
            products.append(product)
        
        # Batch insert all products
        db.add_all(products)
        db.commit()
        
        request.status = 'completed'
        db.commit()
        logger.info(f"Completed processing for request_id: {request_id}")
        
        # Trigger webhook callback if webhook_url is provided
        if request.webhook_url:
            payload = {
                "request_id": request_id,
                "status": request.status
            }
            try:
                response = requests.post(request.webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                logger.info(f"Webhook notified for request_id: {request_id}")
            except Exception as e:
                logger.error(f"Failed to notify webhook for request_id {request_id}: {str(e)}")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing request_id {request_id}: {str(e)}")
        if request:
            request.status = 'failed'
            db.commit()
            # Notify webhook about the failure if webhook_url is provided
            if request.webhook_url:
                payload = {
                    "request_id": request_id,
                    "status": "failed",
                    "error": str(e)
                }
                try:
                    response = requests.post(request.webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
                    logger.info(f"Webhook notified of failure for request_id: {request_id}")
                except Exception as e2:
                    logger.error(f"Failed to notify webhook on failure for request_id {request_id}: {str(e2)}")
    finally:
        db.close()
