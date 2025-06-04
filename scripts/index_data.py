#!/usr/bin/env python3
"""Script to index markdown files from various data directories into ChromaDB."""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if running in virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("ERROR: This script must be run from within the virtual environment!")
    print("\nPlease activate the virtual environment first:")
    print("  source venv/bin/activate  # or .venv/bin/activate")
    print("\nThen run the script again:")
    print("  python scripts/index_data.py")
    sys.exit(1)

try:
    from src.storage.chromadb_client import ChromaDBClient
    from src.storage.collection_manager import CollectionManager
    from src.utils.logging import log_info, log_error, log_warning
    from src.core.config import get_settings
except ImportError as e:
    print(f"ERROR: Failed to import required modules: {e}")
    print("\nMake sure you have activated the virtual environment and installed all dependencies:")
    print("  source venv/bin/activate")
    print("  pip install -r requirements.txt")
    sys.exit(1)


class MarkdownIndexer:
    """Indexes markdown files from specified directories."""
    
    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize the indexer.
        
        Args:
            chromadb_client: ChromaDB client instance
        """
        self.client = chromadb_client
        self.collection_manager = CollectionManager(chromadb_client)
        self.stats = {
            'total_files': 0,
            'indexed_files': 0,
            'failed_files': 0,
            'total_chunks': 0
        }
    
    def read_markdown_file(self, file_path: Path) -> str:
        """Read content from a markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            File content as string
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            log_error(f"Failed to read file {file_path}: {str(e)}")
            return ""
    
    def extract_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from file path and content.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            Dictionary of metadata
        """
        # Determine category based on directory
        category = self._determine_category(file_path)
        
        # Extract title from first heading or filename
        title = self._extract_title(content, file_path)
        
        # Count various content metrics
        metadata = {
            'file_name': file_path.name,
            'file_path': str(file_path),
            'category': category,
            'title': title,
            'word_count': len(content.split()),
            'line_count': len(content.splitlines()),
            'has_code_blocks': '```' in content,
            'has_headings': '#' in content
        }
        
        # Add directory-specific metadata
        if 'meeting_notes' in str(file_path):
            metadata['meeting_type'] = 'scrum' if 'scrum' in str(file_path) else 'general'
        elif 'conversation_notes' in str(file_path):
            metadata['conversation_type'] = 'general'
        
        return metadata
    
    def _determine_category(self, file_path: Path) -> str:
        """Determine category based on file path.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Category string
        """
        path_str = str(file_path).lower()
        
        if 'dmt_notes' in path_str:
            return 'dmt_documentation'
        elif 'va_notes' in path_str:
            return 'va_documentation'
        elif 'conversation_notes' in path_str:
            return 'conversation'
        elif 'meeting_notes' in path_str:
            if 'scrum' in path_str:
                return 'scrum_meeting'
            elif '1on1' in path_str:
                return 'one_on_one_meeting'
            else:
                return 'meeting'
        else:
            return 'documentation'
    
    def _extract_title(self, content: str, file_path: Path) -> str:
        """Extract title from content or filename.
        
        Args:
            content: File content
            file_path: Path to the file
            
        Returns:
            Title string
        """
        # Look for first H1 heading
        lines = content.splitlines()
        for line in lines:
            if line.strip().startswith('# '):
                return line.strip()[2:].strip()
        
        # Fall back to filename without extension
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    async def index_file(self, file_path: Path) -> bool:
        """Index a single markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            log_info(f"Indexing file: {file_path}")
            
            # Read file content
            content = self.read_markdown_file(file_path)
            if not content:
                log_warning(f"Empty or unreadable file: {file_path}")
                return False
            
            # Extract metadata
            metadata = self.extract_metadata(file_path, content)
            
            # Index using collection manager
            ids = self.collection_manager.index_knowledge(
                file_path=file_path,
                content=content,
                category=metadata['category'],
                metadata=metadata
            )
            
            self.stats['indexed_files'] += 1
            self.stats['total_chunks'] += len(ids)
            
            log_info(f"Successfully indexed {file_path} with {len(ids)} chunks")
            return True
            
        except Exception as e:
            log_error(f"Failed to index {file_path}: {str(e)}")
            self.stats['failed_files'] += 1
            return False
    
    async def index_directory(self, directory: Path) -> Dict[str, Any]:
        """Index all markdown files in a directory.
        
        Args:
            directory: Directory path
            
        Returns:
            Dictionary with indexing results
        """
        if not directory.exists():
            log_warning(f"Directory does not exist: {directory}")
            return {'error': f'Directory not found: {directory}'}
        
        # Find all markdown files
        markdown_files = list(directory.rglob('*.md'))
        log_info(f"Found {len(markdown_files)} markdown files in {directory}")
        
        # Index each file
        for file_path in markdown_files:
            self.stats['total_files'] += 1
            await self.index_file(file_path)
        
        return {
            'directory': str(directory),
            'files_found': len(markdown_files),
            'files_indexed': self.stats['indexed_files'],
            'files_failed': self.stats['failed_files']
        }
    
    async def index_all_directories(self, directories: List[Path]) -> Dict[str, Any]:
        """Index all specified directories.
        
        Args:
            directories: List of directory paths
            
        Returns:
            Dictionary with overall results
        """
        results = {}
        
        for directory in directories:
            log_info(f"\n=== Indexing directory: {directory} ===")
            result = await self.index_directory(directory)
            results[str(directory)] = result
        
        return {
            'directories_processed': len(directories),
            'total_files': self.stats['total_files'],
            'indexed_files': self.stats['indexed_files'],
            'failed_files': self.stats['failed_files'],
            'total_chunks': self.stats['total_chunks'],
            'directory_results': results
        }


async def main():
    """Main function to run the indexing process."""
    # Define directories to index
    data_dir = project_root / 'data'
    directories_to_index = [
        data_dir / 'dmt_notes',
        data_dir / 'va_notes',
        data_dir / 'conversation_notes',
        data_dir / 'meeting_notes' / 'scrum'
    ]
    
    # Also check for 1on1 directory
    oneonone_dir = data_dir / 'meeting_notes' / '1on1'
    if oneonone_dir.exists():
        directories_to_index.append(oneonone_dir)
    
    try:
        # Initialize ChromaDB client
        log_info("Initializing ChromaDB client...")
        settings = get_settings()
        chroma_client = ChromaDBClient(
            persist_directory=settings.chroma_persist_directory
        )
        
        # Create indexer
        indexer = MarkdownIndexer(chroma_client)
        
        # Index all directories
        log_info("Starting indexing process...")
        results = await indexer.index_all_directories(directories_to_index)
        
        # Print results
        print("\n=== Indexing Complete ===")
        print(f"Total files processed: {results['total_files']}")
        print(f"Files indexed successfully: {results['indexed_files']}")
        print(f"Files failed: {results['failed_files']}")
        print(f"Total chunks created: {results['total_chunks']}")
        
        print("\n=== Directory Results ===")
        for dir_path, dir_result in results['directory_results'].items():
            print(f"\n{dir_path}:")
            if 'error' in dir_result:
                print(f"  Error: {dir_result['error']}")
            else:
                print(f"  Files found: {dir_result['files_found']}")
                print(f"  Files indexed: {dir_result['files_indexed']}")
                print(f"  Files failed: {dir_result['files_failed']}")
        
        # Get collection stats
        collection_stats = indexer.collection_manager.get_collection_stats()
        print("\n=== Collection Statistics ===")
        for collection_name, stats in collection_stats.items():
            if 'error' not in stats:
                print(f"{collection_name}: {stats['count']} documents")
        
    except Exception as e:
        log_error(f"Indexing failed: {str(e)}")
        print(f"\nError: {str(e)}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))