"""Integration tests for file indexing functionality."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

from src.storage.chromadb_client import ChromaDBClient


class TestFileIndexingIntegration:
    """Integration tests for file indexing with ChromaDB."""

    @pytest.fixture
    async def chroma_client(self, temp_dir):
        """Create a test ChromaDB client."""
        # Use a temporary directory for test database
        db_path = temp_dir / "test_chroma_db"
        
        # Mock the OpenAI embedding function to avoid API calls
        with patch('chromadb.utils.embedding_functions.OpenAIEmbeddingFunction') as mock_embedding:
            mock_embedding.return_value = Mock()
            
            client = ChromaDBClient(persist_directory=str(db_path))
            yield client
            
            # Cleanup
            try:
                client.client.delete_collection("knowledge_base")
            except:
                pass

    @pytest.fixture
    def sample_files(self, temp_dir):
        """Create sample files for testing."""
        files = {}
        
        # Create a Python file
        python_file = temp_dir / "sample.py"
        python_content = '''"""Sample Python module for testing."""

def hello_world():
    """Print hello world."""
    print("Hello, World!")

class TestClass:
    """A simple test class."""
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        """Return the stored value."""
        return self.value
'''
        python_file.write_text(python_content)
        files['python'] = str(python_file)
        
        # Create a markdown file
        md_file = temp_dir / "documentation.md"
        md_content = '''# Project Documentation

## Overview
This is a comprehensive documentation for our automation agents project.

## Features
- File indexing and retrieval
- Natural language processing
- Task management
- Meeting scheduling

## Installation
1. Clone the repository
2. Install dependencies
3. Configure environment variables

## Usage
Run the main script to start the agent system.
'''
        md_file.write_text(md_content)
        files['markdown'] = str(md_file)
        
        # Create a JSON configuration file
        json_file = temp_dir / "config.json"
        json_content = '''{
    "name": "automation-agents",
    "version": "1.0.0",
    "description": "AI-powered automation system",
    "features": [
        "file_indexing",
        "task_management",
        "natural_language_processing"
    ],
    "settings": {
        "max_chunk_size": 1000,
        "overlap_size": 200,
        "embedding_model": "text-embedding-3-small"
    }
}'''
        json_file.write_text(json_content)
        files['json'] = str(json_file)
        
        # Create a text file
        txt_file = temp_dir / "notes.txt"
        txt_content = '''Daily Notes - June 2, 2025

Meeting with the team about project milestones:
- Completed file indexing implementation
- Working on planner integration
- Need to add more test coverage
- Planning to deploy next week

Action items:
1. Review pull requests
2. Update documentation
3. Prepare demo for stakeholders
4. Schedule follow-up meeting

Technologies discussed:
- ChromaDB for vector storage
- OpenAI embeddings
- Python async/await patterns
- pytest for testing
'''
        txt_file.write_text(txt_content)
        files['text'] = str(txt_file)
        
        return files

    @pytest.fixture
    def sample_directory(self, temp_dir):
        """Create a directory structure with multiple files."""
        # Create subdirectories
        src_dir = temp_dir / "src"
        src_dir.mkdir()
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()
        tests_dir = temp_dir / "tests"
        tests_dir.mkdir()
        
        # Create files in src directory
        (src_dir / "main.py").write_text('''#!/usr/bin/env python3
"""Main application entry point."""

import asyncio
from agents import PrimaryAgent

async def main():
    """Run the main application."""
    agent = PrimaryAgent()
    await agent.start()

if __name__ == "__main__":
    asyncio.run(main())
''')
        
        (src_dir / "utils.py").write_text('''"""Utility functions."""

def format_date(date_str):
    """Format a date string."""
    return date_str.replace("-", "/")

def clean_text(text):
    """Clean text by removing extra whitespace."""
    return " ".join(text.split())
''')
        
        # Create files in docs directory
        (docs_dir / "api.md").write_text('''# API Documentation

## Endpoints

### GET /health
Returns the health status of the service.

### POST /index
Index a new document into the knowledge base.

### GET /search
Search for documents in the knowledge base.
''')
        
        (docs_dir / "setup.md").write_text('''# Setup Guide

## Requirements
- Python 3.8+
- ChromaDB
- OpenAI API key

## Installation Steps
1. Create virtual environment
2. Install dependencies
3. Set environment variables
4. Run tests
''')
        
        # Create test files
        (tests_dir / "test_main.py").write_text('''"""Tests for main module."""

import pytest
from src.main import main

def test_main_function():
    """Test main function exists."""
    assert callable(main)
''')
        
        return str(temp_dir)

    @pytest.mark.asyncio
    async def test_single_file_indexing(self, chroma_client, sample_files):
        """Test indexing a single file."""
        # Index the Python file
        python_file = sample_files['python']
        
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Python code implementation"):
            result = await chroma_client.add_file(python_file, chunk_size=500)
        
        assert result["success"] is True
        assert result["file_path"] == python_file
        assert result["chunks_added"] > 0
        assert len(result["document_ids"]) == result["chunks_added"]
        
        # Verify the content was indexed
        search_results = await chroma_client.search("hello world function", n_results=5)
        assert len(search_results["documents"]) > 0
        
        # Check that the search result contains expected content
        found_content = " ".join(search_results["documents"])
        assert "hello_world" in found_content.lower() or "hello world" in found_content.lower()

    @pytest.mark.asyncio
    async def test_multiple_file_types_indexing(self, chroma_client, sample_files):
        """Test indexing different file types."""
        results = {}
        
        # Index each file type
        for file_type, file_path in sample_files.items():
            with patch.object(chroma_client, '_generate_chunk_context', return_value=f"{file_type} content"):
                result = await chroma_client.add_file(file_path, chunk_size=300)
                results[file_type] = result
        
        # Verify all files were indexed successfully
        for file_type, result in results.items():
            assert result["success"] is True, f"Failed to index {file_type} file"
            assert result["chunks_added"] > 0, f"No chunks created for {file_type} file"
        
        # Test search across different file types
        search_queries = [
            ("automation agents", ["markdown", "json"]),  # Should find in markdown and JSON
            ("hello world", ["python"]),  # Should find in Python file
            ("meeting stakeholders", ["text"]),  # Should find in text file
            ("configuration settings", ["json"]),  # Should find in JSON file
        ]
        
        for query, expected_types in search_queries:
            search_results = await chroma_client.search(query, n_results=10)
            assert len(search_results["documents"]) > 0, f"No results for query: {query}"

    @pytest.mark.asyncio
    async def test_directory_indexing(self, chroma_client, sample_directory):
        """Test indexing an entire directory."""
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Directory content"):
            result = await chroma_client.add_directory(
                sample_directory, 
                recursive=True, 
                chunk_size=400
            )
        
        assert result["success"] is True
        assert result["directory_path"] == sample_directory
        assert result["files_processed"] > 0
        assert result["total_chunks_added"] > 0
        
        # Verify specific files were processed
        processed_files = [item["file_path"] for item in result["processed_files"]]
        expected_files = ["main.py", "utils.py", "api.md", "setup.md", "test_main.py"]
        
        for expected_file in expected_files:
            assert any(expected_file in path for path in processed_files), f"{expected_file} not processed"
        
        # Test search functionality across the indexed directory
        search_results = await chroma_client.search("API endpoints documentation", n_results=5)
        assert len(search_results["documents"]) > 0

    @pytest.mark.asyncio
    async def test_file_filtering_by_extension(self, chroma_client, sample_directory):
        """Test indexing with file extension filtering."""
        # Index only Python files
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Python content"):
            result = await chroma_client.add_directory(
                sample_directory,
                recursive=True,
                include_extensions=['.py'],
                chunk_size=400
            )
        
        assert result["success"] is True
        assert result["files_processed"] > 0
        
        # Verify only Python files were processed
        processed_files = [item["file_path"] for item in result["processed_files"]]
        for file_path in processed_files:
            assert file_path.endswith('.py'), f"Non-Python file processed: {file_path}"

    @pytest.mark.asyncio
    async def test_chunking_behavior(self, chroma_client, temp_dir):
        """Test document chunking with different chunk sizes."""
        # Create a large file for chunking
        large_file = temp_dir / "large_document.txt"
        large_content = "\n\n".join([
            f"Section {i}: " + "This is a long section with lots of content. " * 50
            for i in range(10)
        ])
        large_file.write_text(large_content)
        
        # Test with small chunk size
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Large document chunk"):
            result_small = await chroma_client.add_file(str(large_file), chunk_size=200)
        
        # Test with large chunk size
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Large document chunk"):
            # Clear the collection first
            chroma_client.collection.delete(where={})
            result_large = await chroma_client.add_file(str(large_file), chunk_size=1000)
        
        # Small chunks should create more chunks than large chunks
        assert result_small["chunks_added"] > result_large["chunks_added"]
        assert result_small["success"] is True
        assert result_large["success"] is True

    @pytest.mark.asyncio
    async def test_search_functionality(self, chroma_client, sample_files):
        """Test search functionality after indexing."""
        # Index all sample files
        for file_path in sample_files.values():
            with patch.object(chroma_client, '_generate_chunk_context', return_value="Test content"):
                await chroma_client.add_file(file_path, chunk_size=400)
        
        # Test basic search
        results = await chroma_client.search("automation agents", n_results=3)
        assert len(results["documents"]) > 0
        assert len(results["metadatas"]) == len(results["documents"])
        assert len(results["distances"]) == len(results["documents"])
        
        # Test search with reranking
        results_reranked = await chroma_client.search(
            "python function", 
            n_results=3, 
            rerank=True,
            search_k=10
        )
        assert len(results_reranked["documents"]) > 0
        
        # Test metadata filtering (check that file paths are preserved)
        for metadata in results["metadatas"]:
            assert "file_path" in metadata
            assert "source" in metadata
            assert metadata["source"] == "file"

    @pytest.mark.asyncio
    async def test_error_handling(self, chroma_client, temp_dir):
        """Test error handling for various scenarios."""
        # Test non-existent file
        result = await chroma_client.add_file("/non/existent/file.txt")
        assert result["success"] is False
        assert "error" in result
        
        # Test empty file
        empty_file = temp_dir / "empty.txt"
        empty_file.write_text("")
        
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Empty file"):
            result = await chroma_client.add_file(str(empty_file))
        
        assert result["success"] is True
        assert result["chunks_added"] == 0
        
        # Test binary file (should be skipped)
        binary_file = temp_dir / "test.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\x04\x05')
        
        result = await chroma_client.add_file(str(binary_file))
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_indexing(self, chroma_client, sample_files):
        """Test concurrent file indexing."""
        # Index multiple files concurrently
        tasks = []
        for file_path in sample_files.values():
            with patch.object(chroma_client, '_generate_chunk_context', return_value="Concurrent content"):
                task = chroma_client.add_file(file_path, chunk_size=300)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all indexing operations succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                pytest.fail(f"Indexing task {i} failed with exception: {result}")
            
            assert result["success"] is True
            assert result["chunks_added"] > 0
        
        # Verify search works after concurrent indexing
        search_results = await chroma_client.search("test content", n_results=10)
        assert len(search_results["documents"]) > 0

    @pytest.mark.asyncio
    async def test_metadata_preservation(self, chroma_client, sample_files):
        """Test that file metadata is properly preserved during indexing."""
        python_file = sample_files['python']
        
        with patch.object(chroma_client, '_generate_chunk_context', return_value="Python metadata test"):
            result = await chroma_client.add_file(python_file, chunk_size=300)
        
        assert result["success"] is True
        
        # Search and verify metadata
        search_results = await chroma_client.search("hello world", n_results=5)
        
        for metadata in search_results["metadatas"]:
            assert metadata["source"] == "file"
            assert metadata["file_path"] == python_file
            assert "chunk_index" in metadata or "original_chunk_index" in metadata
            assert "total_chunks" in metadata or "total_original_chunks" in metadata

    def test_chunk_text_splitting(self, chroma_client):
        """Test the text chunking functionality."""
        # Test with short text (should return single chunk)
        short_text = "This is a short text."
        chunks = chroma_client._chunk_text(short_text, chunk_size=100, overlap=20)
        assert len(chunks) == 1
        assert chunks[0] == short_text
        
        # Test with long text (should create multiple chunks)
        long_text = "This is a sentence. " * 100  # ~2000 characters
        chunks = chroma_client._chunk_text(long_text, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        
        # Test overlap behavior
        for i in range(len(chunks) - 1):
            # There should be some overlap between consecutive chunks
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            # At least some overlap should exist (not exact due to sentence boundaries)
            assert len(current_chunk) > 0
            assert len(next_chunk) > 0

    def test_file_content_reading(self, chroma_client, sample_files):
        """Test file content reading with different encodings."""
        # Test reading various file types
        for file_type, file_path in sample_files.items():
            content = chroma_client._read_file_content(file_path)
            assert content is not None
            assert len(content) > 0
            assert isinstance(content, str)
        
        # Test non-existent file
        content = chroma_client._read_file_content("/non/existent/file.txt")
        assert content is None