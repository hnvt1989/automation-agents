-- Add user_id column to document_embeddings table for user isolation

-- Add user_id column if it doesn't exist
ALTER TABLE document_embeddings 
ADD COLUMN IF NOT EXISTS user_id UUID;

-- Create index for user_id for better performance
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user_id 
    ON document_embeddings(user_id);

-- Create composite index for user + collection queries
CREATE INDEX IF NOT EXISTS idx_document_embeddings_user_collection 
    ON document_embeddings(user_id, collection_name);

-- Update the match_documents function to include user filtering
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int,
    filter_collection text DEFAULT NULL,
    filter_metadata jsonb DEFAULT NULL,
    filter_user_id uuid DEFAULT NULL
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
        AND (filter_user_id IS NULL OR de.user_id = filter_user_id)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;