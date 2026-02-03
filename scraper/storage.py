import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional



from scraper.models import Tender, RunMetadata

logger = logging.getLogger(__name__)


class TenderStorage:

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_as_json(
        self,
        tenders: List[Tender],
        filename: Optional[str] = None
    ) -> Path:
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"tenders_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        logger.info(f"Saving {len(tenders)} tenders to {filepath}")
        
        data = [tender.model_dump(mode='json') for tender in tenders]
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✓ Saved to {filepath}")
        return filepath

    def save(
        self,
        tenders: List[Tender],
        format: str = 'json',
        filename: Optional[str] = None
    ) -> Path:
        if format == 'json':
            return self.save_as_json(tenders, filename)
        else:
            raise ValueError(f"Unsupported format: {format}")


class MetadataStorage:

    def __init__(self, metadata_dir: Path):
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save_metadata(
        self,
        metadata: RunMetadata,
        filename: Optional[str] = None
    ) -> Path:
        if filename is None:
            filename = f"metadata_{metadata.run_id}.json"
        
        filepath = self.metadata_dir / filename
        
        logger.info(f"Saving run metadata to {filepath}")
        
        data = metadata.model_dump(mode='json')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"✓ Metadata saved to {filepath}")
        return filepath

    def load_metadata(self, run_id: str) -> Optional[RunMetadata]:
        filepath = self.metadata_dir / f"metadata_{run_id}.json"
        
        if not filepath.exists():
            logger.warning(f"Metadata file not found: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return RunMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    def list_runs(self) -> List[str]:
        metadata_files = list(self.metadata_dir.glob("metadata_*.json"))
        run_ids = []
        
        for file in metadata_files:
            run_id = file.stem.replace('metadata_', '')
            run_ids.append(run_id)
        
        return sorted(run_ids)



