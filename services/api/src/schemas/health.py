"""Health Check Schemas."""
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel


class DatabaseHealth(BaseModel):
    connected: bool
    dialect: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    database: DatabaseHealth
    llm_provider: str
    active_plugins: list[str]
