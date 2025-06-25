-- Supabase migrations for enhanced RAG features

-- 1. Add full-text search index to content column
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- For trigram similarity
CREATE EXTENSION IF NOT EXISTS unaccent; -- For accent-insensitive search

-- Create a text search configuration for better search
-- First check if it exists and drop it if needed (for idempotency)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'english_unaccent') THEN
        DROP TEXT SEARCH CONFIGURATION english_unaccent;
    END IF;
END $$;

CREATE TEXT SEARCH CONFIGURATION english_unaccent (COPY = english);
ALTER TEXT SEARCH CONFIGURATION english_unaccent
  ALTER MAPPING FOR hword, hword_part, word
  WITH unaccent, english_stem;

-- Add full-text search column and index
ALTER TABLE document_embeddings 
ADD COLUMN IF NOT EXISTS content_search_vector tsvector 
GENERATED ALWAYS AS (
  setweight(to_tsvector('english_unaccent', coalesce(content, '')), 'A')
) STORED;

-- Create GIN index for full-text search
CREATE INDEX IF NOT EXISTS idx_document_embeddings_content_search 
ON document_embeddings USING GIN(content_search_vector);

-- Create trigram index for fuzzy matching
CREATE INDEX IF NOT EXISTS idx_document_embeddings_content_trgm 
ON document_embeddings USING GIN(content gin_trgm_ops);

-- 2. Add columns for contextual RAG support
ALTER TABLE document_embeddings
ADD COLUMN IF NOT EXISTS original_content TEXT,
ADD COLUMN IF NOT EXISTS has_context BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS context_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS chunk_index INTEGER,
ADD COLUMN IF NOT EXISTS total_chunks INTEGER;

-- 3. Create hybrid search function
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
DECLARE
    max_text_score FLOAT;
BEGIN
    -- Create temporary table for results
    CREATE TEMP TABLE temp_results (
        document_id TEXT,
        content TEXT,
        metadata JSONB,
        similarity_score FLOAT,
        text_score FLOAT
    ) ON COMMIT DROP;
    
    -- Get vector similarity results
    INSERT INTO temp_results
    SELECT 
        de.document_id::TEXT,
        de.content::TEXT,
        de.metadata::JSONB,
        (1 - (de.embedding <=> query_embedding))::FLOAT AS similarity_score,
        0::FLOAT AS text_score
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count * 2;
    
    -- Get full-text search results
    INSERT INTO temp_results
    SELECT 
        de.document_id::TEXT,
        de.content::TEXT,
        de.metadata::JSONB,
        0::FLOAT AS similarity_score,
        ts_rank(de.content_search_vector, websearch_to_tsquery('english_unaccent', query_text))::FLOAT AS text_score
    FROM document_embeddings de
    WHERE
        de.content_search_vector @@ websearch_to_tsquery('english_unaccent', query_text)
        AND (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
        AND de.document_id NOT IN (SELECT document_id FROM temp_results)
    ORDER BY text_score DESC
    LIMIT match_count * 2;
    
    -- Normalize text scores
    SELECT MAX(text_score) INTO max_text_score FROM temp_results WHERE text_score > 0;
    IF max_text_score IS NULL OR max_text_score = 0 THEN
        max_text_score := 1;
    END IF;
    
    -- Return combined results
    RETURN QUERY
    SELECT 
        r.document_id,
        r.content,
        r.metadata,
        MAX(r.similarity_score) AS similarity_score,
        MAX(r.text_score / max_text_score) AS text_score,
        (alpha * MAX(r.similarity_score) + (1 - alpha) * MAX(r.text_score / max_text_score))::FLOAT AS combined_score
    FROM temp_results r
    GROUP BY r.document_id, r.content, r.metadata
    ORDER BY combined_score DESC
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

-- 5. Create index for faster contextual queries
CREATE INDEX IF NOT EXISTS idx_document_embeddings_has_context 
ON document_embeddings(has_context) 
WHERE has_context = TRUE;

-- 6. Create composite index for collection queries
CREATE INDEX IF NOT EXISTS idx_document_embeddings_collection_embedding 
ON document_embeddings(collection_name, embedding);

-- 7. Add support for metadata search
CREATE INDEX IF NOT EXISTS idx_document_embeddings_metadata 
ON document_embeddings USING GIN(metadata);

-- 8. Create view for collection statistics
CREATE OR REPLACE VIEW collection_stats AS
SELECT 
    collection_name,
    COUNT(*) as document_count,
    COUNT(CASE WHEN has_context = TRUE THEN 1 END) as contextual_count,
    AVG(LENGTH(content)) as avg_content_length,
    MAX(created_at) as last_updated
FROM document_embeddings
GROUP BY collection_name;

-- 9. Grant permissions (adjust based on your Supabase setup)
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT SELECT ON collection_stats TO anon, authenticated;
GRANT EXECUTE ON FUNCTION hybrid_search TO anon, authenticated;
GRANT EXECUTE ON FUNCTION contextual_search TO anon, authenticated;
GRANT EXECUTE ON FUNCTION match_documents TO anon, authenticated;