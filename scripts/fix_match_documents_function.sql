-- Fix the match_documents function to handle type conversions properly

-- Drop the existing function first
DROP FUNCTION IF EXISTS match_documents(vector, integer, text, jsonb);

-- Recreate with proper type casting
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int,
    filter_collection text DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL
)
RETURNS TABLE (
    document_id text,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.document_id::text,
        de.content::text,
        de.metadata::jsonb,
        (1 - (de.embedding <=> query_embedding))::float AS similarity
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Also fix the get_collection_stats function if needed
DROP FUNCTION IF EXISTS get_collection_stats();

CREATE OR REPLACE FUNCTION get_collection_stats()
RETURNS TABLE (
    collection_name text,
    document_count bigint,
    avg_content_length float,
    total_size_bytes bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.collection_name::text,
        COUNT(*)::bigint as document_count,
        AVG(LENGTH(de.content))::float as avg_content_length,
        SUM(pg_column_size(de.*))::bigint as total_size_bytes
    FROM document_embeddings de
    GROUP BY de.collection_name
    ORDER BY de.collection_name;
END;
$$;