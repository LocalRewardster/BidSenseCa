-- Migration to update tenders table schema to match scraper and backend expectations

-- Add missing columns (only if they don't exist)
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS category TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS reference TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS contact_name TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS contact_email TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS contact_phone TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS source_url TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS closing_date DATE;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS organization TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS contract_value TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS source_name TEXT;

-- Copy data from old columns to new columns
UPDATE tenders SET source_name = source WHERE source_name IS NULL;
UPDATE tenders SET organization = buyer WHERE organization IS NULL;
UPDATE tenders SET description = summary_ai WHERE description IS NULL;
UPDATE tenders SET closing_date = deadline WHERE closing_date IS NULL;

-- Make the old source column nullable since we now have source_name
ALTER TABLE tenders ALTER COLUMN source DROP NOT NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tenders_source_name ON tenders(source_name);
CREATE INDEX IF NOT EXISTS idx_tenders_organization ON tenders(organization);
CREATE INDEX IF NOT EXISTS idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(category);
CREATE INDEX IF NOT EXISTS idx_tenders_external_id_source ON tenders(external_id, source_name);

-- Create a view that maps old field names to new ones for backward compatibility
CREATE OR REPLACE VIEW tenders_v2 AS
SELECT 
    id,
    source_name,
    external_id,
    title,
    organization,
    province,
    naics,
    closing_date,
    description,
    tags_ai,
    scraped_at,
    scraped_at AS created_at,
    scraped_at AS updated_at,
    category,
    reference,
    contact_name,
    contact_email,
    contact_phone,
    source_url,
    contract_value
FROM tenders;

-- Add comments for documentation
COMMENT ON TABLE tenders IS 'Updated schema to match scraper and backend service expectations';
COMMENT ON COLUMN tenders.source_name IS 'Source name (e.g., canadabuys, ontario_portal)';
COMMENT ON COLUMN tenders.organization IS 'Organization/buyer name';
COMMENT ON COLUMN tenders.description IS 'Tender description';
COMMENT ON COLUMN tenders.closing_date IS 'Tender closing date';
COMMENT ON COLUMN tenders.category IS 'Tender category';
COMMENT ON COLUMN tenders.reference IS 'Tender reference number';
COMMENT ON COLUMN tenders.contact_name IS 'Contact person name';
COMMENT ON COLUMN tenders.contact_email IS 'Contact email';
COMMENT ON COLUMN tenders.contact_phone IS 'Contact phone';
COMMENT ON COLUMN tenders.source_url IS 'URL to the original tender';
COMMENT ON COLUMN tenders.contract_value IS 'Contract value'; 