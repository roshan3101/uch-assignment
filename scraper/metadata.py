"""Run metadata tracking and management."""

import logging
from datetime import datetime
from typing import Any, Dict

from scraper.models import RunMetadata, TenderType

logger = logging.getLogger(__name__)


class MetadataTracker:

    def __init__(self, run_id: str, scraper_version: str, config: Dict[str, Any]):
        self.metadata = RunMetadata(
            run_id=run_id,
            start_time=datetime.utcnow(),
            scraper_version=scraper_version,
            config=config
        )
        
        logger.info(f"Started tracking run: {run_id}")

    def increment_pages(self, count: int = 1):
        self.metadata.pages_visited += count

    def increment_parsed(self, count: int = 1):
        self.metadata.tenders_parsed += count

    def increment_saved(self, count: int = 1):
        self.metadata.tenders_saved += count

    def increment_failures(self, count: int = 1):
        self.metadata.failures += count

    def set_deduped_count(self, count: int):
        self.metadata.deduped_count = count

    def update_tender_types(self, tender_types: Dict[str, int]):
        self.metadata.tender_types_processed = tender_types

    def add_error(self, error_type: str, message: str):
        self.metadata.add_error(error_type, message)

    def set_output_file(self, filepath: str):
        self.metadata.output_file = filepath

    def finalize(self) -> RunMetadata:
        self.metadata.end_time = datetime.utcnow()
        self.metadata.calculate_duration()
        
        logger.info(
            f"Run {self.metadata.run_id} completed: "
            f"{self.metadata.tenders_saved} tenders saved, "
            f"{self.metadata.failures} failures, "
            f"{self.metadata.duration_seconds:.2f}s"
        )
        
        return self.metadata

    def get_metadata(self) -> RunMetadata:
        return self.metadata


def generate_run_id() -> str:
    return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def count_tender_types(tenders: list) -> Dict[str, int]:
    counts: Dict[str, int] = {
        TenderType.GOODS.value: 0,
        TenderType.WORKS.value: 0,
        TenderType.SERVICES.value: 0,
        TenderType.UNKNOWN.value: 0,
    }
    
    for tender in tenders:
        tender_type = tender.tender_type
        if tender_type in counts:
            counts[tender_type] += 1
        else:
            counts[TenderType.UNKNOWN.value] += 1
    
    return counts
