-- Migration to add rich metadata fields for CanadaBuys scraper enhancement
-- Based on PRD requirements for summary_raw, documents_urls, and original_url

-- Add new columns for rich metadata (only if they don't exist)
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS summary_raw TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS documents_urls TEXT[];
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS original_url TEXT;

-- Create indexes for better performance on new fields
CREATE INDEX IF NOT EXISTS idx_tenders_summary_raw ON tenders USING gin(to_tsvector('english', summary_raw));
CREATE INDEX IF NOT EXISTS idx_tenders_documents_urls ON tenders USING gin(documents_urls);
CREATE INDEX IF NOT EXISTS idx_tenders_original_url ON tenders(original_url);

-- Drop the existing view first to avoid conflicts
DROP VIEW IF EXISTS tenders_v2;

-- Recreate the view to include new fields
CREATE VIEW tenders_v2 AS
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
    summary_raw,
    documents_urls,
    original_url,
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
COMMENT ON COLUMN tenders.summary_raw IS 'Raw summary text from tender description (before AI processing)';
COMMENT ON COLUMN tenders.documents_urls IS 'Array of document URLs (PDF, DOCX, ZIP attachments)';
COMMENT ON COLUMN tenders.original_url IS 'Canonical URL to the original tender notice';

-- Create a function to search within summary_raw text
CREATE OR REPLACE FUNCTION search_tenders_summary(search_term TEXT)
RETURNS TABLE (
    id UUID,
    title TEXT,
    summary_raw TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.title,
        t.summary_raw,
        ts_rank(to_tsvector('english', t.summary_raw), plainto_tsquery('english', search_term)) as similarity
    FROM tenders t
    WHERE t.summary_raw IS NOT NULL
    AND to_tsvector('english', t.summary_raw) @@ plainto_tsquery('english', search_term)
    ORDER BY similarity DESC;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get tenders with documents
CREATE OR REPLACE FUNCTION get_tenders_with_documents()
RETURNS TABLE (
    id UUID,
    title TEXT,
    organization TEXT,
    documents_count INTEGER,
    documents_urls TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.title,
        t.organization,
        array_length(t.documents_urls, 1) as documents_count,
        t.documents_urls
    FROM tenders t
    WHERE t.documents_urls IS NOT NULL
    AND array_length(t.documents_urls, 1) > 0
    ORDER BY array_length(t.documents_urls, 1) DESC;
END;
$$ LANGUAGE plpgsql; 