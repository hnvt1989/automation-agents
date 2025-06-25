-- Supabase functions for vector similarity search

-- Function to perform similarity search on document embeddings
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_count int DEFAULT 5,
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
        de.document_id,
        de.content,
        de.metadata::jsonb,
        1 - (de.embedding <=> query_embedding) AS similarity
    FROM document_embeddings de
    WHERE
        (filter_collection IS NULL OR de.collection_name = filter_collection)
        AND (filter_metadata IS NULL OR de.metadata @> filter_metadata)
    ORDER BY de.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to get documents by collection
CREATE OR REPLACE FUNCTION get_collection_documents(
    collection_name_filter text,
    max_results int DEFAULT 100
)
RETURNS TABLE (
    document_id text,
    content text,
    metadata jsonb,
    created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.document_id,
        de.content,
        de.metadata::jsonb,
        de.created_at
    FROM document_embeddings de
    WHERE de.collection_name = collection_name_filter
    ORDER BY de.created_at DESC
    LIMIT max_results;
END;
$$;

-- Function to get collection statistics
CREATE OR REPLACE FUNCTION get_collection_stats()
RETURNS TABLE (
    collection_name text,
    document_count bigint,
    avg_content_length float,
    last_updated timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.collection_name,
        COUNT(*)::bigint as document_count,
        AVG(LENGTH(de.content))::float as avg_content_length,
        MAX(de.updated_at) as last_updated
    FROM document_embeddings de
    GROUP BY de.collection_name
    ORDER BY document_count DESC;
END;
$$;

-- Create RLS policies for secure access (adjust based on your auth setup)
-- Example: Allow authenticated users to read all documents
CREATE POLICY "Allow authenticated read access" ON document_embeddings
    FOR SELECT USING (auth.role() = 'authenticated');

-- Example: Allow authenticated users to insert documents
CREATE POLICY "Allow authenticated insert access" ON document_embeddings
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Example: Allow authenticated users to update their own documents
CREATE POLICY "Allow authenticated update access" ON document_embeddings
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Example: Allow authenticated users to delete their own documents
CREATE POLICY "Allow authenticated delete access" ON document_embeddings
    FOR DELETE USING (auth.role() = 'authenticated');