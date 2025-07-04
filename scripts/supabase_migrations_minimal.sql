-- Supabase migrations for enhanced RAG features (Minimal version)
-- This version skips large indexes that might cause memory issues

-- 1. Add extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- 2. Add columns for contextual RAG support
ALTER TABLE document_embeddings
ADD COLUMN IF NOT EXISTS original_content TEXT,
ADD COLUMN IF NOT EXISTS has_context BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS context_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
ADD COLUMN IF NOT EXISTS total_chunks INTEGER;

-- 3. Create hybrid search function (simplified without full-text search)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    match_count INT,
    alpha FLOAT DEFAULT 0.7,
    filter_collection TEXT DEFAULT NULL,
    filter_metadata JSONB DEFAULT NULL
)
RETURNS TABLE (
    document_id TEXT,
    content TEXT,
    metadata JSONB,
    similarity_score FLOAT,
    text_score FLOAT,
    combined_score FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- For now, just return vector search results
    -- Full-text search can be added later when resources allow
    RETURN QUERY
    SELECT 
        de.document_id::TEXT,
        de.content::TEXT,
        de.metadata::JSONB,
        (1 - (de.embedding <=> query_embedding))::FLOAT AS similarity_score,
        0.0::FLOAT AS text_score,
        (1 - (de.embedding <=> query_embedding))::FLOAT AS combined_score
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 4. Create function for contextual search
CREATE OR REPLACE FUNCTION contextual_search(
    query_embedding vector(1536),
    match_count INT,
    filter_collection TEXT DEFAULT NULL,
    filter_metadata JSONB DEFAULT NULL,
    prefer_contextual BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
    document_id TEXT,
    content TEXT,
    original_content TEXT,
    metadata JSONB,
    similarity FLOAT,
    has_context BOOLEAN
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.document_id::TEXT,
        de.content::TEXT,
        de.original_content::TEXT,
        de.metadata::JSONB,
        (1 - (de.embedding <=> query_embedding))::FLOAT AS similarity,
        de.has_context::BOOLEAN
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
        AND (NOT prefer_contextual OR de.has_context = TRUE OR de.has_context IS NULL)
    ORDER BY 
        CASE WHEN prefer_contextual AND de.has_context = TRUE THEN 0 ELSE 1 END,
        de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- 5. Create simple index for contextual queries (smaller index)
CREATE INDEX IF NOT EXISTS idx_document_embeddings_has_context 
ON document_embeddings(has_context, collection_name) 
WHERE has_context = TRUE;

-- 6. Create view for collection statistics
CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    collection_name,
    COUNT(*) as document_count,
    COUNT(CASE WHEN has_context = TRUE THEN 1 END) as contextual_count,
    AVG(LENGTH(content)) as avg_content_length,
    MAX(created_at) as last_updated
FROM document_embeddings
GROUP BY collection_name;

-- 7. Grant permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON collection_stats TO anon, authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO anon, authenticated;
GRANT EXECUTE ON FUNCTION contextual_search TO anon, authenticated;
GRANT EXECUTE ON FUNCTION match_documents TO anon, authenticated;