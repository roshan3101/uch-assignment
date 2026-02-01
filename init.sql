CREATE TABLE IF NOT EXISTS tenders (
    id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) UNIQUE NOT NULL,
    tender_type VARCHAR(20),
    tender_status VARCHAR(20),
    title TEXT NOT NULL,
    organization TEXT NOT NULL,
    publish_date DATE,
    closing_date DATE,
    estimated_value NUMERIC(15, 2),
    description TEXT,
    source_url TEXT NOT NULL,
    ifb_number VARCHAR(100),
    document_count INTEGER,
    location TEXT,
    department TEXT,
    category TEXT,
    attachments JSONB DEFAULT '[]'::jsonb,
    raw_html_snippet TEXT,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenders_tender_id ON tenders(tender_id);
CREATE INDEX IF NOT EXISTS idx_tenders_tender_type ON tenders(tender_type);
CREATE INDEX IF NOT EXISTS idx_tenders_organization ON tenders(organization);
CREATE INDEX IF NOT EXISTS idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX IF NOT EXISTS idx_tenders_ingested_at ON tenders(ingested_at);

CREATE TABLE IF NOT EXISTS run_metadata (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) UNIQUE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds NUMERIC(10, 2),
    scraper_version VARCHAR(20),
    config JSONB DEFAULT '{}'::jsonb,
    pages_visited INTEGER DEFAULT 0,
    tenders_parsed INTEGER DEFAULT 0,
    tenders_saved INTEGER DEFAULT 0,
    failures INTEGER DEFAULT 0,
    deduped_count INTEGER DEFAULT 0,
    tender_types_processed JSONB DEFAULT '{}'::jsonb,
    error_summary JSONB DEFAULT '{}'::jsonb,
    output_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_run_metadata_run_id ON run_metadata(run_id);
CREATE INDEX IF NOT EXISTS idx_run_metadata_start_time ON run_metadata(start_time);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tenders_updated_at
    BEFORE UPDATE ON tenders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO scraper;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO scraper;
