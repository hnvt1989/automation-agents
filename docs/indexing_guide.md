# Document Indexing Guide

This guide explains how to index documents from your local directories to cloud services (Supabase for vector search and Neo4j Aura for knowledge graphs).

## Quick Start

To index the default directories (`data/meeting_notes` and `data/va_notes`):

```bash
./index_docs.sh
```

## Prerequisites

1. **Cloud Services Configured**: Ensure you have set up:
   - Supabase project with pgvector enabled
   - Neo4j Aura instance
   - Environment variables in `local.env`:
     ```env
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_KEY=your_supabase_anon_key
     NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
     NEO4J_USER=neo4j
     NEO4J_PASSWORD=your_password
     ```

2. **Document Directories**: Place your documents in:
   - `data/meeting_notes/` - Meeting notes and minutes
   - `data/va_notes/` - VA-related notes and documentation

## Usage

### Basic Indexing

```bash
# Index default directories
./index_docs.sh

# Or run directly
python scripts/index_to_cloud.py
```

### Custom Directories

```bash
# Index specific directories
./index_docs.sh --directories data/custom_dir1 data/custom_dir2

# Index with specific file extensions
./index_docs.sh --extensions .md .txt .doc
```

### Advanced Options

```bash
# Clear existing data before indexing
./index_docs.sh --clear

# Use a custom collection name
./index_docs.sh --collection my_custom_collection

# Use a different environment file
./index_docs.sh --env-file production.env
```

## What Gets Indexed

### Vector Storage (Supabase)
- Document content is split into chunks with context
- Each chunk is embedded using OpenAI's text-embedding-ada-002
- Metadata includes:
  - Source file path
  - Document type (meeting/va_note)
  - Date (extracted from filename if present)
  - Title (extracted from content)
  - Chunk position information

### Knowledge Graph (Neo4j)
- **Document Nodes**: Each file becomes a Document node
- **Entity Nodes**: Extracted entities include:
  - Dates mentioned in documents
  - Email addresses
  - Topics (from headings)
  - Action items (TODO, follow-ups)
- **Directory Nodes**: Each indexed directory
- **Relationships**:
  - Directory -[CONTAINS]-> Document
  - Document -[MENTIONS]-> Entity

## Entity Extraction

The indexer automatically extracts:

1. **Dates**: Various formats (MM/DD/YYYY, YYYY-MM-DD, etc.)
2. **Emails**: Standard email addresses
3. **Topics**: From markdown headings
4. **Action Items**: Patterns like:
   - TODO: ...
   - Action: ...
   - Follow-up: ...
   - - [ ] Markdown checkboxes

## File Format Support

By default, the indexer processes:
- `.md` - Markdown files
- `.txt` - Plain text files

You can add more extensions using the `--extensions` flag.

## Monitoring Progress

The script provides detailed logging:
- Files being processed
- Chunks created per file
- Entities extracted
- Success/failure counts
- Final statistics

## Troubleshooting

### Common Issues

1. **"Supabase credentials not found"**
   - Ensure `SUPABASE_URL` and `SUPABASE_KEY` are in your `local.env`
   - Check that you're using the correct env file

2. **"Neo4j Aura credentials not found"**
   - Ensure `NEO4J_URI` and `NEO4J_PASSWORD` are set
   - URI should start with `neo4j+s://` for cloud instances

3. **"Directory not found"**
   - Use relative paths from project root
   - Or use absolute paths

4. **Encoding errors**
   - The script assumes UTF-8 encoding
   - Convert files to UTF-8 if needed

### Performance Tips

1. **Batch Processing**: The script processes files sequentially. For large datasets:
   - Consider indexing in batches
   - Use `--clear` carefully to avoid re-indexing

2. **Chunk Size**: Default chunk size is optimized for most use cases
   - Smaller chunks = more precise search but more storage
   - Larger chunks = more context but less precision

3. **Rate Limits**: Be aware of:
   - OpenAI API rate limits for embeddings
   - Supabase request limits
   - Neo4j Aura connection limits

## Querying Indexed Data

After indexing, you can search your documents:

### Using the RAG Agent

```bash
# Start the main application
./run.sh

# Then query:
"Search for meeting notes about project planning"
"Find all action items from last week"
"Show me documents mentioning budget discussions"
```

### Using the API

```python
from src.agents.rag_cloud import CloudRAGAgent

# Search vector storage
result = await rag_agent.run("Search for information about Q4 planning")

# Search knowledge graph
result = await rag_agent.run("Find all entities related to 'budget'")
```

## Best Practices

1. **Document Organization**:
   - Use consistent naming conventions
   - Include dates in filenames (YYYY-MM-DD format)
   - Use clear headings in markdown

2. **Content Structure**:
   - Start documents with a clear title
   - Use markdown headings for sections
   - Mark action items clearly

3. **Regular Updates**:
   - Re-index periodically for new documents
   - Consider incremental indexing for large collections

4. **Metadata**:
   - The indexer extracts metadata automatically
   - Consider adding frontmatter to markdown files for additional metadata

## Example Document Structure

```markdown
# Team Meeting - Project Alpha
Date: 2024-01-15

## Attendees
- John Doe (john@example.com)
- Jane Smith (jane@example.com)

## Discussion Points

### Budget Review
- Current spend: $45,000
- Projected Q1: $60,000
- TODO: Prepare detailed budget breakdown

### Timeline Updates
- Phase 1: Complete by 2024-02-01
- Phase 2: Start 2024-02-15

## Action Items
- [ ] John: Send updated budget report
- [ ] Jane: Schedule follow-up meeting
- [ ] Team: Review project timeline

## Next Meeting
2024-01-22 at 10:00 AM
```

This structure helps the indexer extract:
- Title and date
- Email addresses
- Topics (Budget Review, Timeline Updates)
- Action items
- Future dates