-- Migration to add advanced search vector for full-text search capabilities
-- This enables boolean operators, phrase search, and field-specific filtering

-- Add search_vector column with comprehensive text indexing
ALTER TABLE tenders 
  ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (
      to_tsvector('english',
        coalesce(title,'') || ' ' ||
        coalesce(summary_raw,'') || ' ' ||
        coalesce(organization,'') || ' ' ||
        coalesce(description,'') || ' ' ||
        coalesce(category,'') || ' ' ||
        coalesce(reference,'') || ' ' ||
        coalesce(naics,'')
      )
    ) STORED;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS tenders_fts_idx ON tenders USING GIN (search_vector);

-- Create additional index for ranking performance
CREATE INDEX IF NOT EXISTS tenders_fts_rank_idx ON tenders USING GIN (search_vector) WITH (fastupdate = off);

-- Create function to search with highlighting
CREATE OR REPLACE FUNCTION search_tenders_advanced(
    search_query TEXT,
    buyer_filter TEXT DEFAULT NULL,
    province_filter TEXT DEFAULT NULL,
    naics_filter TEXT DEFAULT NULL,
    limit_count INTEGER DEFAULT 50,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    organization TEXT,
    description TEXT,
    summary_raw TEXT,
    category TEXT,
    reference TEXT,
    naics TEXT,
    province TEXT,
    closing_date DATE,
    contract_value TEXT,
    source_name TEXT,
    contact_name TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    documents_urls TEXT[],
    original_url TEXT,
    rank DOUBLE PRECISION,
    highlight TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.title,
        t.organization,
        t.description,
        t.summary_raw,
        t.category,
        t.reference,
        t.naics,
        t.province,
        t.closing_date,
        t.contract_value,
        t.source_name,
        t.contact_name,
        t.contact_email,
        t.contact_phone,
        t.documents_urls,
        t.original_url,
        ts_rank(t.search_vector, to_tsquery('english', search_query))::DOUBLE PRECISION AS rank,
        ts_headline('english', 
                   COALESCE(t.summary_raw, t.description, ''), 
                   to_tsquery('english', search_query),
                   'MaxFragments=2, MinWords=5, MaxWords=15, StartSel=<mark>, StopSel=</mark>') AS highlight
    FROM tenders t
    WHERE t.search_vector @@ to_tsquery('english', search_query)
      AND (buyer_filter IS NULL OR t.organization ILIKE '%' || buyer_filter || '%')
      AND (province_filter IS NULL OR t.province = province_filter)
      AND (naics_filter IS NULL OR t.naics = naics_filter)
    ORDER BY rank DESC
    LIMIT limit_count OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get search suggestions
CREATE OR REPLACE FUNCTION get_search_suggestions_advanced(
    query_prefix TEXT,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    suggestion TEXT,
    type TEXT,
    frequency INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        word AS suggestion,
        'word' AS type,
        COUNT(*) AS frequency
    FROM (
        SELECT unnest(regexp_split_to_array(
            lower(COALESCE(title, '') || ' ' || 
                  COALESCE(organization, '') || ' ' || 
                  COALESCE(category, '')),
            '\s+'
        )) AS word
        FROM tenders
        WHERE title ILIKE query_prefix || '%' 
           OR organization ILIKE query_prefix || '%'
           OR category ILIKE query_prefix || '%'
    ) words
    WHERE word ILIKE query_prefix || '%'
      AND length(word) > 2
    GROUP BY word
    ORDER BY frequency DESC, word
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get search statistics
CREATE OR REPLACE FUNCTION get_search_statistics()
RETURNS TABLE (
    total_tenders INTEGER,
    tenders_with_summary INTEGER,
    tenders_with_documents INTEGER,
    tenders_with_contacts INTEGER,
    avg_search_vector_length INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::INTEGER AS total_tenders,
        COUNT(CASE WHEN summary_raw IS NOT NULL AND summary_raw != '' THEN 1 END)::INTEGER AS tenders_with_summary,
        COUNT(CASE WHEN documents_urls IS NOT NULL AND array_length(documents_urls, 1) > 0 THEN 1 END)::INTEGER AS tenders_with_documents,
        COUNT(CASE WHEN contact_name IS NOT NULL OR contact_email IS NOT NULL OR contact_phone IS NOT NULL THEN 1 END)::INTEGER AS tenders_with_contacts,
        AVG(length(search_vector::text))::INTEGER AS avg_search_vector_length
    FROM tenders;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON COLUMN tenders.search_vector IS 'Generated full-text search vector for advanced search capabilities';
COMMENT ON FUNCTION search_tenders_advanced IS 'Advanced search function with boolean operators, highlighting, and field filtering';
COMMENT ON FUNCTION get_search_suggestions_advanced IS 'Get search suggestions based on title, organization, and category';
COMMENT ON FUNCTION get_search_statistics IS 'Get search-related statistics for the tenders table';

-- Create rollback function (for testing)
CREATE OR REPLACE FUNCTION rollback_advanced_search()
RETURNS VOID AS $$
BEGIN
    DROP INDEX IF EXISTS tenders_fts_rank_idx;
    DROP INDEX IF EXISTS tenders_fts_idx;
    ALTER TABLE tenders DROP COLUMN IF EXISTS search_vector;
    DROP FUNCTION IF EXISTS search_tenders_advanced;
    DROP FUNCTION IF EXISTS get_search_suggestions_advanced;
    DROP FUNCTION IF EXISTS get_search_statistics;
END;
$$ LANGUAGE plpgsql;

-- Add performance monitoring view
CREATE OR REPLACE VIEW search_performance_stats AS
SELECT 
    schemaname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE indexrelname LIKE '%fts%' OR indexrelname LIKE '%search%';

COMMENT ON VIEW search_performance_stats IS 'Monitor search index performance and usage'; 