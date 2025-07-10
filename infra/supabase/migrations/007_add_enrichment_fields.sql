-- Migration: Add enrichment tracking fields
-- Description: Add fields to track manual enrichment status and timestamps

-- Add enrichment tracking columns
ALTER TABLE tenders 
ADD COLUMN IF NOT EXISTS enriched BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

-- Add indexes for enrichment queries
CREATE INDEX IF NOT EXISTS idx_tenders_enriched ON tenders(enriched);
CREATE INDEX IF NOT EXISTS idx_tenders_enriched_at ON tenders(enriched_at);

-- Add composite index for completeness queries
CREATE INDEX IF NOT EXISTS idx_tenders_completeness ON tenders(enriched, scraped_at) 
WHERE enriched = FALSE;

-- Add function to calculate completeness score
CREATE OR REPLACE FUNCTION calculate_tender_completeness(tender_row tenders)
RETURNS FLOAT AS $$
DECLARE
    total_fields INTEGER := 5;
    available_fields INTEGER := 0;
BEGIN
    -- Count available critical fields
    IF tender_row.contact_name IS NOT NULL AND tender_row.contact_name != '' THEN
        available_fields := available_fields + 1;
    END IF;
    
    IF tender_row.contact_email IS NOT NULL AND tender_row.contact_email != '' THEN
        available_fields := available_fields + 1;
    END IF;
    
    IF tender_row.closing_date IS NOT NULL THEN
        available_fields := available_fields + 1;
    END IF;
    
    IF tender_row.documents_urls IS NOT NULL AND array_length(tender_row.documents_urls, 1) > 0 THEN
        available_fields := available_fields + 1;
    END IF;
    
    IF tender_row.selection_criteria IS NOT NULL AND tender_row.selection_criteria != '' THEN
        available_fields := available_fields + 1;
    END IF;
    
    RETURN available_fields::FLOAT / total_fields::FLOAT;
END;
$$ LANGUAGE plpgsql;

-- Add function to get incomplete tenders
CREATE OR REPLACE FUNCTION get_incomplete_tenders(
    completeness_threshold FLOAT DEFAULT 0.8,
    days_back INTEGER DEFAULT 30,
    limit_count INTEGER DEFAULT 100
)
RETURNS TABLE (
    id UUID,
    external_id TEXT,
    title TEXT,
    organization TEXT,
    source_url TEXT,
    source_name TEXT,
    completeness_score FLOAT,
    missing_fields TEXT[],
    scraped_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.external_id,
        t.title,
        COALESCE(t.organization, t.buyer) as organization,
        t.source_url,
        t.source_name,
        calculate_tender_completeness(t) as completeness_score,
        ARRAY[
            CASE WHEN t.contact_name IS NULL OR t.contact_name = '' THEN 'Contact Name' ELSE NULL END,
            CASE WHEN t.contact_email IS NULL OR t.contact_email = '' THEN 'Contact Email' ELSE NULL END,
            CASE WHEN t.closing_date IS NULL THEN 'Closing Date' ELSE NULL END,
            CASE WHEN t.documents_urls IS NULL OR array_length(t.documents_urls, 1) = 0 THEN 'Attachments' ELSE NULL END,
            CASE WHEN t.selection_criteria IS NULL OR t.selection_criteria = '' THEN 'Site Meeting Info' ELSE NULL END
        ]::TEXT[] as missing_fields,
        t.scraped_at
    FROM tenders t
    WHERE 
        t.enriched = FALSE
        AND t.scraped_at > (NOW() - INTERVAL '%s days', days_back)
        AND calculate_tender_completeness(t) <= completeness_threshold
    ORDER BY t.scraped_at DESC
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Add function to get enrichment statistics
CREATE OR REPLACE FUNCTION get_enrichment_stats()
RETURNS TABLE (
    total_tenders BIGINT,
    enriched_tenders BIGINT,
    pending_enrichment BIGINT,
    avg_completeness FLOAT,
    recent_enrichments BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_tenders,
        COUNT(*) FILTER (WHERE enriched = TRUE) as enriched_tenders,
        COUNT(*) FILTER (WHERE enriched = FALSE) as pending_enrichment,
        AVG(calculate_tender_completeness(t)) as avg_completeness,
        COUNT(*) FILTER (WHERE enriched_at > NOW() - INTERVAL '7 days') as recent_enrichments
    FROM tenders t
    WHERE scraped_at > NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON COLUMN tenders.enriched IS 'Whether this tender has been manually enriched with additional data';
COMMENT ON COLUMN tenders.enriched_at IS 'Timestamp when manual enrichment was completed';

COMMENT ON FUNCTION calculate_tender_completeness(tenders) IS 'Calculate completeness score (0-1) based on critical fields availability';
COMMENT ON FUNCTION get_incomplete_tenders(FLOAT, INTEGER, INTEGER) IS 'Get tenders that need manual enrichment based on completeness threshold';
COMMENT ON FUNCTION get_enrichment_stats() IS 'Get statistics about enrichment progress and completion rates'; 