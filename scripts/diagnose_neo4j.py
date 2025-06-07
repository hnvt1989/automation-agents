#!/usr/bin/env python3
"""
Neo4j Database Diagnostic Script

This script checks the current state of the Neo4j database to identify
missing properties and schema issues causing the warnings in the logs.
"""

import asyncio
import os
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    from src.utils.logging import log_info, log_error, log_warning
except ImportError:
    # Fallback to simple print statements
    def log_info(msg): print(f"INFO: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")


class Neo4jDiagnostics:
    """Diagnose Neo4j database schema and data issues."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
    
    async def initialize(self):
        """Initialize Neo4j connection."""
        if not NEO4J_AVAILABLE:
            log_error("Neo4j driver not available. Install with: pip install neo4j")
            return False
        
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            # Test connection
            await self.driver.verify_connectivity()
            log_info("Connected to Neo4j successfully")
            return True
        except Exception as e:
            log_error(f"Failed to connect to Neo4j: {e}")
            return False
    
    async def check_database_state(self) -> Dict[str, Any]:
        """Check the current state of the database."""
        if not self.driver:
            return {"error": "Not connected to database"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check if database is empty
                result = await session.run("MATCH (n) RETURN count(n) as node_count")
                record = await result.single()
                results["total_nodes"] = record["node_count"] if record else 0
                
                result = await session.run("MATCH ()-[r]->() RETURN count(r) as edge_count")
                record = await result.single()
                results["total_edges"] = record["edge_count"] if record else 0
                
                log_info(f"Database contains {results['total_nodes']} nodes and {results['total_edges']} edges")
                
                if results["total_nodes"] == 0:
                    results["status"] = "empty"
                    return results
                
                # Check node labels
                result = await session.run("""
                    MATCH (n) 
                    RETURN DISTINCT labels(n) as labels, count(*) as count
                    ORDER BY count DESC
                """)
                results["node_labels"] = []
                async for record in result:
                    results["node_labels"].append({
                        "labels": record["labels"],
                        "count": record["count"]
                    })
                
                # Check relationship types
                result = await session.run("""
                    MATCH ()-[r]->() 
                    RETURN type(r) as rel_type, count(*) as count
                    ORDER BY count DESC
                """)
                results["relationship_types"] = []
                async for record in result:
                    results["relationship_types"].append({
                        "type": record["rel_type"],
                        "count": record["count"]
                    })
                
                results["status"] = "populated"
                return results
                
        except Exception as e:
            log_error(f"Error checking database state: {e}")
            results["error"] = str(e)
            return results
    
    async def check_entity_properties(self) -> Dict[str, Any]:
        """Check properties on Entity nodes."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check if Entity nodes exist
                result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
                record = await result.single()
                entity_count = record["count"] if record else 0
                results["entity_count"] = entity_count
                
                if entity_count == 0:
                    log_warning("No Entity nodes found in database")
                    return results
                
                # Check properties on Entity nodes
                result = await session.run("""
                    MATCH (n:Entity) 
                    RETURN keys(n) as properties, count(*) as count
                    ORDER BY count DESC
                    LIMIT 10
                """)
                results["entity_properties"] = []
                async for record in result:
                    results["entity_properties"].append({
                        "properties": record["properties"],
                        "count": record["count"]
                    })
                
                # Check specifically for missing embedding properties
                result = await session.run("""
                    MATCH (n:Entity) 
                    RETURN 
                        count(n) as total,
                        count(n.name_embedding) as with_name_embedding,
                        count(n.summary) as with_summary,
                        count(n.uuid) as with_uuid,
                        count(n.name) as with_name
                """)
                record = await result.single()
                if record:
                    results["embedding_analysis"] = {
                        "total_entities": record["total"],
                        "with_name_embedding": record["with_name_embedding"],
                        "with_summary": record["with_summary"],
                        "with_uuid": record["with_uuid"],
                        "with_name": record["with_name"]
                    }
                
                return results
                
        except Exception as e:
            log_error(f"Error checking entity properties: {e}")
            results["error"] = str(e)
            return results
    
    async def check_relationship_properties(self) -> Dict[str, Any]:
        """Check properties on RELATES_TO relationships."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check if RELATES_TO relationships exist
                result = await session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
                record = await result.single()
                rel_count = record["count"] if record else 0
                results["relates_to_count"] = rel_count
                
                if rel_count == 0:
                    log_warning("No RELATES_TO relationships found in database")
                    return results
                
                # Check properties on RELATES_TO relationships
                result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->() 
                    RETURN keys(r) as properties, count(*) as count
                    ORDER BY count DESC
                    LIMIT 10
                """)
                results["relationship_properties"] = []
                async for record in result:
                    results["relationship_properties"].append({
                        "properties": record["properties"],
                        "count": record["count"]
                    })
                
                # Check specifically for missing embedding properties
                result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->() 
                    RETURN 
                        count(r) as total,
                        count(r.fact_embedding) as with_fact_embedding,
                        count(r.episodes) as with_episodes,
                        count(r.fact) as with_fact,
                        count(r.uuid) as with_uuid
                """)
                record = await result.single()
                if record:
                    results["embedding_analysis"] = {
                        "total_relationships": record["total"],
                        "with_fact_embedding": record["with_fact_embedding"],
                        "with_episodes": record["with_episodes"],
                        "with_fact": record["with_fact"],
                        "with_uuid": record["with_uuid"]
                    }
                
                return results
                
        except Exception as e:
            log_error(f"Error checking relationship properties: {e}")
            results["error"] = str(e)
            return results
    
    async def check_indexes_and_constraints(self) -> Dict[str, Any]:
        """Check what indexes and constraints exist."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check indexes
                result = await session.run("SHOW INDEXES")
                results["indexes"] = []
                async for record in result:
                    results["indexes"].append(dict(record))
                
                # Check constraints
                result = await session.run("SHOW CONSTRAINTS")
                results["constraints"] = []
                async for record in result:
                    results["constraints"].append(dict(record))
                
                return results
                
        except Exception as e:
            log_error(f"Error checking indexes and constraints: {e}")
            results["error"] = str(e)
            return results
    
    async def sample_data(self) -> Dict[str, Any]:
        """Get sample data to understand structure."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Sample Entity nodes
                result = await session.run("""
                    MATCH (n:Entity) 
                    RETURN n 
                    LIMIT 3
                """)
                results["sample_entities"] = []
                async for record in result:
                    node = record["n"]
                    results["sample_entities"].append({
                        "labels": list(node.labels),
                        "properties": dict(node)
                    })
                
                # Sample relationships
                result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->() 
                    RETURN r 
                    LIMIT 3
                """)
                results["sample_relationships"] = []
                async for record in result:
                    rel = record["r"]
                    results["sample_relationships"].append({
                        "type": rel.type,
                        "properties": dict(rel)
                    })
                
                return results
                
        except Exception as e:
            log_error(f"Error sampling data: {e}")
            results["error"] = str(e)
            return results
    
    async def close(self):
        """Close database connection."""
        if self.driver:
            await self.driver.close()


async def main():
    """Main diagnostic function."""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv("local.env")
    except ImportError:
        log_warning("python-dotenv not installed, using os.environ")
    
    # Get Neo4j connection details
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    log_info("=== Neo4j Database Diagnostics ===")
    log_info(f"Connecting to: {neo4j_uri}")
    
    diagnostics = Neo4jDiagnostics(neo4j_uri, neo4j_user, neo4j_password)
    
    if not await diagnostics.initialize():
        log_error("Failed to connect to Neo4j. Check connection details.")
        return
    
    try:
        # Check overall database state
        log_info("\n1. Checking database state...")
        db_state = await diagnostics.check_database_state()
        if "error" in db_state:
            log_error(f"Database state check failed: {db_state['error']}")
        else:
            log_info(f"Status: {db_state.get('status', 'unknown')}")
            log_info(f"Total nodes: {db_state.get('total_nodes', 0)}")
            log_info(f"Total edges: {db_state.get('total_edges', 0)}")
            
            if db_state.get("node_labels"):
                log_info("Node labels:")
                for label_info in db_state["node_labels"]:
                    log_info(f"  {label_info['labels']}: {label_info['count']} nodes")
            
            if db_state.get("relationship_types"):
                log_info("Relationship types:")
                for rel_info in db_state["relationship_types"]:
                    log_info(f"  {rel_info['type']}: {rel_info['count']} relationships")
        
        # Check Entity properties
        log_info("\n2. Checking Entity node properties...")
        entity_props = await diagnostics.check_entity_properties()
        if "error" in entity_props:
            log_error(f"Entity properties check failed: {entity_props['error']}")
        else:
            log_info(f"Entity nodes found: {entity_props.get('entity_count', 0)}")
            
            if entity_props.get("embedding_analysis"):
                analysis = entity_props["embedding_analysis"]
                log_info("Entity embedding analysis:")
                log_info(f"  Total entities: {analysis['total_entities']}")
                log_info(f"  With name_embedding: {analysis['with_name_embedding']}")
                log_info(f"  With summary: {analysis['with_summary']}")
                log_info(f"  With uuid: {analysis['with_uuid']}")
                log_info(f"  With name: {analysis['with_name']}")
                
                if analysis['with_name_embedding'] == 0 and analysis['total_entities'] > 0:
                    log_warning("❌ ISSUE: Entities exist but have no name_embedding property!")
        
        # Check relationship properties
        log_info("\n3. Checking RELATES_TO relationship properties...")
        rel_props = await diagnostics.check_relationship_properties()
        if "error" in rel_props:
            log_error(f"Relationship properties check failed: {rel_props['error']}")
        else:
            log_info(f"RELATES_TO relationships found: {rel_props.get('relates_to_count', 0)}")
            
            if rel_props.get("embedding_analysis"):
                analysis = rel_props["embedding_analysis"]
                log_info("Relationship embedding analysis:")
                log_info(f"  Total relationships: {analysis['total_relationships']}")
                log_info(f"  With fact_embedding: {analysis['with_fact_embedding']}")
                log_info(f"  With episodes: {analysis['with_episodes']}")
                log_info(f"  With fact: {analysis['with_fact']}")
                log_info(f"  With uuid: {analysis['with_uuid']}")
                
                if analysis['with_fact_embedding'] == 0 and analysis['total_relationships'] > 0:
                    log_warning("❌ ISSUE: Relationships exist but have no fact_embedding property!")
        
        # Check indexes and constraints
        log_info("\n4. Checking indexes and constraints...")
        indexes_constraints = await diagnostics.check_indexes_and_constraints()
        if "error" in indexes_constraints:
            log_error(f"Indexes/constraints check failed: {indexes_constraints['error']}")
        else:
            log_info(f"Indexes found: {len(indexes_constraints.get('indexes', []))}")
            log_info(f"Constraints found: {len(indexes_constraints.get('constraints', []))}")
        
        # Sample data
        log_info("\n5. Sampling data...")
        sample_data = await diagnostics.sample_data()
        if "error" in sample_data:
            log_error(f"Data sampling failed: {sample_data['error']}")
        else:
            if sample_data.get("sample_entities"):
                log_info("Sample Entity nodes:")
                for i, entity in enumerate(sample_data["sample_entities"]):
                    log_info(f"  Entity {i+1}: {entity['properties'].keys()}")
            
            if sample_data.get("sample_relationships"):
                log_info("Sample RELATES_TO relationships:")
                for i, rel in enumerate(sample_data["sample_relationships"]):
                    log_info(f"  Relationship {i+1}: {rel['properties'].keys()}")
        
        # Summary and recommendations
        log_info("\n=== DIAGNOSTIC SUMMARY ===")
        
        issues_found = []
        if db_state.get("total_nodes", 0) == 0:
            issues_found.append("Database is empty - no nodes or relationships found")
        else:
            if entity_props.get("embedding_analysis", {}).get("with_name_embedding", 0) == 0:
                issues_found.append("Entity nodes missing name_embedding property")
            if rel_props.get("embedding_analysis", {}).get("with_fact_embedding", 0) == 0:
                issues_found.append("RELATES_TO relationships missing fact_embedding property")
            if rel_props.get("embedding_analysis", {}).get("with_episodes", 0) == 0:
                issues_found.append("RELATES_TO relationships missing episodes property")
        
        if issues_found:
            log_warning("Issues found:")
            for issue in issues_found:
                log_warning(f"  ❌ {issue}")
            
            log_info("\nRecommended actions:")
            if db_state.get("total_nodes", 0) == 0:
                log_info("  1. Initialize knowledge graph with sample data")
                log_info("  2. Run schema migration to create proper structure")
            else:
                log_info("  1. Run schema migration to add missing properties")
                log_info("  2. Regenerate embeddings for existing data")
                log_info("  3. Update code to handle missing embeddings gracefully")
        else:
            log_info("✅ No major issues found!")
    
    finally:
        await diagnostics.close()


if __name__ == "__main__":
    asyncio.run(main())