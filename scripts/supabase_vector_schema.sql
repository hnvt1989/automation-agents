-- Schema for vector storage using pgvector extension

-- Enable pgvector extension (run as superuser if needed)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create table for document embeddings
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    collection_name VARCHAR(255) NOT NULL,
    document_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 embeddings are 1536 dimensions
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Create unique constraint on collection + document_id
    UNIQUE(collection_name, document_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_embeddings_collection 
    ON document_embeddings(collection_name);

CREATE INDEX IF NOT EXISTS idx_document_embeddings_document_id 
    ON document_embeddings(document_id);

CREATE INDEX IF NOT EXISTS idx_document_embeddings_metadata 
    ON document_embeddings USING GIN (metadata);

-- Create HNSW index for vector similarity search (much faster than default)
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector 
    ON document_embeddings USING hnsw (embedding vector_cosine_ops);

-- Function for similarity search
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

-- Function to get collection statistics
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

-- Trigger to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_document_embeddings_updated_at 
    BEFORE UPDATE ON document_embeddings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Sample usage comments
COMMENT ON TABLE document_embeddings IS 'Stores document embeddings for vector similarity search';
COMMENT ON COLUMN document_embeddings.embedding IS 'OpenAI text-embedding-ada-002 vector (1536 dimensions)';
COMMENT ON FUNCTION match_documents IS 'Performs cosine similarity search on document embeddings';

-- Grant permissions (adjust as needed)
-- GRANT USAGE ON SCHEMA public TO authenticated;
-- GRANT ALL ON TABLE document_embeddings TO authenticated;
-- GRANT EXECUTE ON FUNCTION match_documents TO authenticated;
-- GRANT EXECUTE ON FUNCTION get_collection_stats TO authenticated;