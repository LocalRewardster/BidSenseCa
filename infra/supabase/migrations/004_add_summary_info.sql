-- Migration to add summary information fields for CanadaBuys scraper enhancement
-- Based on the sidebar summary information from CanadaBuys tender pages

-- Add new columns for summary information (only if they don't exist)
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS notice_type TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS languages TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS delivery_regions TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS opportunity_region TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS contract_duration TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS procurement_method TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS selection_criteria TEXT;
ALTER TABLE tenders ADD COLUMN IF NOT EXISTS commodity_unspsc TEXT;

-- Create indexes for better performance on new fields
CREATE INDEX IF NOT EXISTS idx_tenders_notice_type ON tenders(notice_type);
CREATE INDEX IF NOT EXISTS idx_tenders_languages ON tenders USING gin(to_tsvector('english', languages));
CREATE INDEX IF NOT EXISTS idx_tenders_delivery_regions ON tenders USING gin(to_tsvector('english', delivery_regions));
CREATE INDEX IF NOT EXISTS idx_tenders_procurement_method ON tenders(procurement_method);
CREATE INDEX IF NOT EXISTS idx_tenders_selection_criteria ON tenders(selection_criteria);

-- Drop the existing view first to avoid column conflicts
DROP VIEW IF EXISTS tenders_v2;

-- Recreate the view with the new columns
CREATE VIEW tenders_v2 AS
SELECT 
    id,
    source_name,
    external_id,
    title,
    organization,
    description,
    contract_value,
    closing_date,
    source_url,
    location,
    category,
    reference,
    contact_name,
    contact_email,
    contact_phone,
    summary_raw,
    documents_urls,
    original_url,
    -- New summary information fields
    notice_type,
    languages,
    delivery_regions,
    opportunity_region,
    contract_duration,
    procurement_method,
    selection_criteria,
    commodity_unspsc,
    scraped_at,
    -- AI-generated fields (if they exist)
    COALESCE(summary_ai, '') as summary_ai,
    COALESCE(tags_ai, '') as tags_ai
FROM tenders;

-- Add helper functions for the new fields
CREATE OR REPLACE FUNCTION get_tenders_by_notice_type(notice_type_filter TEXT)
RETURNS TABLE (
    id UUID,
    title TEXT,
    organization TEXT,
    notice_type TEXT,
    closing_date TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.id, t.title, t.organization, t.notice_type, t.closing_date
    FROM tenders t
    WHERE t.notice_type ILIKE '%' || notice_type_filter || '%'
    ORDER BY t.closing_date DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_tenders_by_procurement_method(method_filter TEXT)
RETURNS TABLE (
    id UUID,
    title TEXT,
    organization TEXT,
    procurement_method TEXT,
    closing_date TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT t.id, t.title, t.organization, t.procurement_method, t.closing_date
    FROM tenders t
    WHERE t.procurement_method ILIKE '%' || method_filter || '%'
    ORDER BY t.closing_date DESC;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON COLUMN tenders.notice_type IS 'Type of tender notice (e.g., Request for Proposal, Standing Offer)';
COMMENT ON COLUMN tenders.languages IS 'Languages in which the tender is available';
COMMENT ON COLUMN tenders.delivery_regions IS 'Regions where goods/services will be delivered';
COMMENT ON COLUMN tenders.opportunity_region IS 'Region where the opportunity is available';
COMMENT ON COLUMN tenders.contract_duration IS 'Duration of the contract';
COMMENT ON COLUMN tenders.procurement_method IS 'Method of procurement (e.g., Competitive - Open Bidding)';
COMMENT ON COLUMN tenders.selection_criteria IS 'Criteria for selecting the winning bid';
COMMENT ON COLUMN tenders.commodity_unspsc IS 'UNSPSC commodity codes for the tender'; 