"""Storage modules for data persistence."""
from .chromadb_client import ChromaDBClient, get_chromadb_client
from .collection_manager import CollectionManager

# Optional graph support
try:
    from .graph_knowledge_manager import GraphKnowledgeManager
    __all__ = ["ChromaDBClient", "get_chromadb_client", "CollectionManager", "GraphKnowledgeManager"]
except ImportError:
    # Graph support not available
    __all__ = ["ChromaDBClient", "get_chromadb_client", "CollectionManager"]