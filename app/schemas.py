from pydantic import BaseModel
from uuid import UUID

class CSVUploadResponse(BaseModel):
    request_id: UUID

class StatusResponse(BaseModel):
    status: str

class WebhookNotification(BaseModel):
    status: str
    request_id: UUID
    error: str = None