from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TenderType(str, Enum):
    GOODS = "Goods"
    WORKS = "Works"
    SERVICES = "Services"
    UNKNOWN = "Unknown"


class TenderStatus(str, Enum):
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"
    AWARDED = "Awarded"
    CANCELLED = "Cancelled"
    UNKNOWN = "Unknown"


class Attachment(BaseModel):
    name: str = Field(..., description="Attachment filename")
    url: Optional[str] = Field(None, description="Download URL")
    size: Optional[str] = Field(None, description="File size")
    type: Optional[str] = Field(None, description="File type/extension")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "tender_document.pdf",
                "url": "https://tender.nprocure.com/documents/123.pdf",
                "size": "2.5 MB",
                "type": "pdf"
            }
        }


class Tender(BaseModel):
    
    tender_id: str = Field(..., description="Unique tender identifier")
    title: str = Field(..., description="Tender title/name of work")
    organization: str = Field(..., description="Issuing organization")
    
    tender_type: TenderType = Field(
        default=TenderType.UNKNOWN,
        description="Type of tender (Goods/Works/Services)"
    )
    tender_status: TenderStatus = Field(
        default=TenderStatus.IN_PROGRESS,
        description="Current status of the tender"
    )
    
    publish_date: Optional[str] = Field(
        None,
        description="Publication date (YYYY-MM-DD format)"
    )
    closing_date: Optional[str] = Field(
        None,
        description="Submission deadline (YYYY-MM-DD format)"
    )
    
    estimated_value: Optional[float] = Field(
        None,
        description="Estimated contract value",
        ge=0
    )
    
    description: Optional[str] = Field(
        None,
        description="Tender description/details"
    )
    
    source_url: str = Field(..., description="Source URL of the tender")
    ifb_number: Optional[str] = Field(
        None,
        description="IFB/Tender Notice Number"
    )
    
    attachments: List[Attachment] = Field(
        default_factory=list,
        description="List of tender documents/attachments"
    )
    document_count: Optional[int] = Field(
        None,
        description="Total number of documents",
        ge=0
    )
    
    location: Optional[str] = Field(None, description="Project location")
    department: Optional[str] = Field(None, description="Department name")
    category: Optional[str] = Field(None, description="Tender category")
    
    raw_html_snippet: Optional[str] = Field(
        None,
        description="Raw HTML snippet for debugging"
    )
    ingested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was scraped"
    )
    
    @field_validator("publish_date", "closing_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        if len(v) == 10 and v[4] == "-" and v[7] == "-":
            return v
        
        return v
    
    @field_validator("description", "title")
    @classmethod
    def clean_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        cleaned = " ".join(v.split())
        return cleaned if cleaned else None

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "tender_id": "271843",
                "tender_type": "Works",
                "title": "Construction of Various Category Quarters in Ahmedabad City",
                "organization": "R&B-Shahibag R and B Sub. Division, Ahmedabad",
                "publish_date": "2025-12-15",
                "closing_date": "2026-02-10",
                "estimated_value": 431999.99,
                "description": "Construction of Five (5) New E-2 Type Bungalows...",
                "source_url": "https://tender.nprocure.com/view-nit-home?id=271843",
                "attachments": [],
                "document_count": 12,
                "ingested_at": "2026-02-01T16:45:00Z"
            }
        }


class RunMetadata(BaseModel):
    
    run_id: str = Field(..., description="Unique run identifier")
    start_time: datetime = Field(..., description="Run start timestamp")
    end_time: Optional[datetime] = Field(None, description="Run end timestamp")
    duration_seconds: Optional[float] = Field(
        None,
        description="Total run duration in seconds",
        ge=0
    )
    
    scraper_version: str = Field(..., description="Scraper version")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Configuration used for this run"
    )
    
    pages_visited: int = Field(default=0, description="Total pages visited", ge=0)
    tenders_parsed: int = Field(default=0, description="Tenders parsed", ge=0)
    tenders_saved: int = Field(default=0, description="Tenders saved", ge=0)
    failures: int = Field(default=0, description="Number of failures", ge=0)
    deduped_count: int = Field(default=0, description="Duplicates removed", ge=0)
    
    tender_types_processed: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by tender type"
    )
    
    error_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of errors encountered"
    )
    
    output_file: Optional[str] = Field(None, description="Output file path")
    
    def calculate_duration(self) -> None:
        if self.end_time:
            delta = self.end_time - self.start_time
            self.duration_seconds = delta.total_seconds()
    
    def add_error(self, error_type: str, message: str) -> None:
        if error_type not in self.error_summary:
            self.error_summary[error_type] = []
        self.error_summary[error_type].append({
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.failures += 1

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "run_20260201_164500",
                "start_time": "2026-02-01T16:45:00Z",
                "end_time": "2026-02-01T17:30:00Z",
                "duration_seconds": 2700,
                "scraper_version": "1.0.0",
                "config": {
                    "rate_limit": 1.0,
                    "concurrency": 3,
                    "limit": None
                },
                "pages_visited": 4303,
                "tenders_parsed": 4303,
                "tenders_saved": 4298,
                "failures": 5,
                "deduped_count": 12,
                "tender_types_processed": {
                    "Works": 2150,
                    "Goods": 1200,
                    "Services": 948
                },
                "error_summary": {},
                "output_file": "data/output/tenders_20260201_164500.json"
            }
        }
