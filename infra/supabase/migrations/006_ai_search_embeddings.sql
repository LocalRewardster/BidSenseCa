-- Migration for AI Search with pgvector embeddings
-- This enables vector similarity search for AI-powered tender search

-- Enable pgvector extension (should already be enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tender_embeddings table if it doesn't exist
CREATE TABLE IF NOT EXISTS tender_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tender_id UUID NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
    embedding VECTOR(1536), -- OpenAI embedding dimension
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for tender_embeddings table
CREATE UNIQUE INDEX IF NOT EXISTS idx_tender_embeddings_tender_id ON tender_embeddings(tender_id);
CREATE INDEX IF NOT EXISTS idx_tender_embeddings_embedding ON tender_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function to search tenders with hybrid ranking (vector + text)
CREATE OR REPLACE FUNCTION search_tenders_ai(
    search_query TEXT,
    query_embedding VECTOR(1536),
    province_filter TEXT DEFAULT NULL,
    min_value DECIMAL DEFAULT NULL,
    max_value DECIMAL DEFAULT NULL,
    deadline_before DATE DEFAULT NULL,
    deadline_after DATE DEFAULT NULL,
    limit_count INTEGER DEFAULT 20,
    offset_count INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    title TEXT,
    summary_raw TEXT,
    buyer TEXT,
    category TEXT,
    external_id TEXT,
    naics TEXT,
    province TEXT,
    value DECIMAL,
    deadline DATE,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE,
    score DOUBLE PRECISION,
    cosine_similarity DOUBLE PRECISION,
    text_rank DOUBLE PRECISION,
    province_bonus DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        t.title,
        t.summary_raw,
        t.buyer,
        t.category,
        t.external_id,
        t.naics,
        t.province,
        t.value,
        t.deadline,
        t.url,
        t.created_at,
        t.updated_at,
        -- Hybrid score: 60% vector similarity + 30% text rank + 10% province bonus
        (
            0.6 * COALESCE(1 - (te.embedding <=> query_embedding), 0) +
            0.3 * COALESCE(ts_rank(t.search_vector, plainto_tsquery('english', search_query)), 0) +
            0.1 * CASE 
                WHEN t.province ILIKE '%' || COALESCE(province_filter, '') || '%' THEN 1.0
                ELSE 0.0
            END
        ) as score,
        -- Cosine similarity
        COALESCE(1 - (te.embedding <=> query_embedding), 0) as cosine_similarity,
        -- Text rank
        COALESCE(ts_rank(t.search_vector, plainto_tsquery('english', search_query)), 0) as text_rank,
        -- Province bonus
        CASE 
            WHEN t.province ILIKE '%' || COALESCE(province_filter, '') || '%' THEN 1.0
            ELSE 0.0
        END as province_bonus
    FROM tenders t
    LEFT JOIN tender_embeddings te ON t.id = te.tender_id
    WHERE 
        -- Basic filters
        (province_filter IS NULL OR t.province ILIKE '%' || province_filter || '%')
        AND (min_value IS NULL OR t.value >= min_value)
        AND (max_value IS NULL OR t.value <= max_value)
        AND (deadline_before IS NULL OR t.deadline <= deadline_before)
        AND (deadline_after IS NULL OR t.deadline >= deadline_after)
        -- Text search
        AND (search_query = '' OR t.search_vector @@ plainto_tsquery('english', search_query))
    ORDER BY score DESC
    LIMIT limit_count
    OFFSET offset_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get total count for AI search
CREATE OR REPLACE FUNCTION search_tenders_ai_count(
    search_query TEXT,
    province_filter TEXT DEFAULT NULL,
    min_value DECIMAL DEFAULT NULL,
    max_value DECIMAL DEFAULT NULL,
    deadline_before DATE DEFAULT NULL,
    deadline_after DATE DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    count_result INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO count_result
    FROM tenders t
    WHERE 
        -- Basic filters
        (province_filter IS NULL OR t.province ILIKE '%' || province_filter || '%')
        AND (min_value IS NULL OR t.value >= min_value)
        AND (max_value IS NULL OR t.value <= max_value)
        AND (deadline_before IS NULL OR t.deadline <= deadline_before)
        AND (deadline_after IS NULL OR t.deadline >= deadline_after)
        -- Text search
        AND (search_query = '' OR t.search_vector @@ plainto_tsquery('english', search_query));
    
    RETURN count_result;
END;
$$ LANGUAGE plpgsql;

-- Function to insert or update tender embedding
CREATE OR REPLACE FUNCTION upsert_tender_embedding(
    p_tender_id UUID,
    p_embedding VECTOR(1536)
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO tender_embeddings (tender_id, embedding)
    VALUES (p_tender_id, p_embedding)
    ON CONFLICT (tender_id)
    DO UPDATE SET 
        embedding = EXCLUDED.embedding,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql; 