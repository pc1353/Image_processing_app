# Use a slim Python 3.9 base image to keep the image size small
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements.txt file to install dependencies
COPY requirements.txt .

# Install system dependencies and Python packages
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean

# Copy the entire project directory into the container
COPY . .

# Create the directory for processed images
RUN mkdir -p /app/processed_images

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Run the database initialization and start the FastAPI server
CMD python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000