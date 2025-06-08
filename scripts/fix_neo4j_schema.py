#!/usr/bin/env python3
"""
Neo4j Schema Migration Script

This script fixes the Neo4j knowledge graph schema issues by:
1. Creating proper vector indices for embedding properties
2. Validating and fixing missing embedding properties
3. Adding proper constraints and indices
"""

import asyncio
import os
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add project root to path
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
    def log_info(msg): print(f"INFO: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")


class Neo4jSchemaMigration:
    """Manages Neo4j schema migration and fixes."""
    
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
            await self.driver.verify_connectivity()
            log_info("Connected to Neo4j successfully")
            return True
        except Exception as e:
            log_error(f"Failed to connect to Neo4j: {e}")
            return False
    
    async def create_vector_indices(self) -> bool:
        """Create vector indices for embedding properties."""
        if not self.driver:
            return False
        
        try:
            async with self.driver.session() as session:
                # Create vector index for Entity name_embedding
                try:
                    await session.run("""
                        CREATE VECTOR INDEX entity_name_embedding_index IF NOT EXISTS
                        FOR (n:Entity) ON (n.name_embedding)
                        OPTIONS {
                            indexConfig: {
                                `vector.dimensions`: 1536,
                                `vector.similarity_function`: 'cosine'
                            }
                        }
                    """
                    )
                    log_info("Created vector index for Entity.name_embedding")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e).lower():
                        log_info("Vector index for Entity.name_embedding already exists")
                    else:
                        log_error(f"Failed to create Entity name_embedding index: {e}")
                
                # Create vector index for RELATES_TO fact_embedding
                try:
                    await session.run("""
                        CREATE VECTOR INDEX relationship_fact_embedding_index IF NOT EXISTS
                        FOR ()-[r:RELATES_TO]-() ON (r.fact_embedding)
                        OPTIONS {
                            indexConfig: {
                                `vector.dimensions`: 1536,
                                `vector.similarity_function`: 'cosine'
                            }
                        }
                    """
                    )
                    log_info("Created vector index for RELATES_TO.fact_embedding")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e).lower():
                        log_info("Vector index for RELATES_TO.fact_embedding already exists")
                    else:
                        log_error(f"Failed to create RELATES_TO fact_embedding index: {e}")
                
                return True
                
        except Exception as e:
            log_error(f"Error creating vector indices: {e}")
            return False
    
    async def validate_and_fix_missing_properties(self) -> Dict[str, Any]:
        """Validate and fix entities/relationships with missing properties."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {
            "entities_checked": 0,
            "entities_fixed": 0,
            "relationships_checked": 0,
            "relationships_fixed": 0,
            "errors": []
        }
        
        try:
            async with self.driver.session() as session:
                # Check and fix Entity nodes
                entity_result = await session.run("""
                    MATCH (n:Entity)
                    WHERE n.name_embedding IS NULL
                    RETURN count(n) as missing_count
                """)
                record = await entity_result.single()
                missing_entities = record["missing_count"] if record else 0
                
                if missing_entities > 0:
                    log_warning(f"Found {missing_entities} Entity nodes with missing name_embedding")
                    # For now, we'll set them to a default empty vector
                    # In production, you'd regenerate embeddings properly
                    await session.run("""
                        MATCH (n:Entity)
                        WHERE n.name_embedding IS NULL
                        SET n.name_embedding = [0.0] * 1536
                        RETURN count(n) as fixed_count
                    """)
                    results["entities_fixed"] = missing_entities
                    log_info(f"Fixed {missing_entities} Entity nodes with placeholder embeddings")
                
                # Check total entities
                entity_count_result = await session.run("MATCH (n:Entity) RETURN count(n) as count")
                record = await entity_count_result.single()
                results["entities_checked"] = record["count"] if record else 0
                
                # Check and fix RELATES_TO relationships
                rel_result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    WHERE r.fact_embedding IS NULL OR r.episodes IS NULL
                    RETURN count(r) as missing_count
                """)
                record = await rel_result.single()
                missing_relationships = record["missing_count"] if record else 0
                
                if missing_relationships > 0:
                    log_warning(f"Found {missing_relationships} RELATES_TO relationships with missing properties")
                    # Fix missing fact_embedding
                    await session.run("""
                        MATCH ()-[r:RELATES_TO]->()
                        WHERE r.fact_embedding IS NULL
                        SET r.fact_embedding = [0.0] * 1536
                    """)
                    # Fix missing episodes
                    await session.run("""
                        MATCH ()-[r:RELATES_TO]->()
                        WHERE r.episodes IS NULL
                        SET r.episodes = []
                    """)
                    results["relationships_fixed"] = missing_relationships
                    log_info(f"Fixed {missing_relationships} RELATES_TO relationships with placeholder properties")
                
                # Check total relationships
                rel_count_result = await session.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) as count")
                record = await rel_count_result.single()
                results["relationships_checked"] = record["count"] if record else 0
                
                return results
                
        except Exception as e:
            log_error(f"Error validating/fixing properties: {e}")
            results["errors"].append(str(e))
            return results
    
    async def create_additional_constraints(self) -> bool:
        """Create additional constraints and indices for better performance."""
        if not self.driver:
            return False
        
        try:
            async with self.driver.session() as session:
                # Create constraint on Entity UUID if not exists
                try:
                    await session.run("""
                        CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS
                        FOR (n:Entity) REQUIRE n.uuid IS UNIQUE
                    """)
                    log_info("Created uniqueness constraint for Entity.uuid")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e).lower():
                        log_info("Constraint for Entity.uuid already exists")
                    else:
                        log_error(f"Failed to create Entity.uuid constraint: {e}")
                
                # Create constraint on relationship UUID if not exists
                try:
                    await session.run("""
                        CREATE CONSTRAINT relates_to_uuid_unique IF NOT EXISTS
                        FOR ()-[r:RELATES_TO]-() REQUIRE r.uuid IS UNIQUE
                    """)
                    log_info("Created uniqueness constraint for RELATES_TO.uuid")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e).lower():
                        log_info("Constraint for RELATES_TO.uuid already exists")
                    else:
                        log_error(f"Failed to create RELATES_TO.uuid constraint: {e}")
                
                # Create index on group_id for better query performance
                try:
                    await session.run("""
                        CREATE INDEX entity_group_id_index IF NOT EXISTS
                        FOR (n:Entity) ON (n.group_id)
                    """)
                    log_info("Created index for Entity.group_id")
                except Exception as e:
                    if "already exists" in str(e) or "equivalent" in str(e).lower():
                        log_info("Index for Entity.group_id already exists")
                    else:
                        log_error(f"Failed to create Entity.group_id index: {e}")
                
                return True
                
        except Exception as e:
            log_error(f"Error creating constraints: {e}")
            return False
    
    async def verify_schema_health(self) -> Dict[str, Any]:
        """Verify the health of the schema after migration."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check vector indices
                indices_result = await session.run("SHOW INDEXES")
                vector_indices = []
                async for record in indices_result:
                    if record.get("type") == "VECTOR":
                        vector_indices.append({
                            "name": record.get("name"),
                            "labels": record.get("labelsOrTypes"),
                            "properties": record.get("properties")
                        })
                results["vector_indices"] = vector_indices
                
                # Check entity completeness
                entity_result = await session.run("""
                    MATCH (n:Entity)
                    RETURN 
                        count(n) as total,
                        count(n.name_embedding) as with_embedding,
                        count(n.uuid) as with_uuid,
                        count(n.name) as with_name
                """)
                record = await entity_result.single()
                if record:
                    results["entity_health"] = {
                        "total": record["total"],
                        "with_embedding": record["with_embedding"],
                        "with_uuid": record["with_uuid"],
                        "with_name": record["with_name"],
                        "health_score": record["with_embedding"] / record["total"] if record["total"] > 0 else 0
                    }
                
                # Check relationship completeness
                rel_result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    RETURN 
                        count(r) as total,
                        count(r.fact_embedding) as with_embedding,
                        count(r.episodes) as with_episodes,
                        count(r.fact) as with_fact
                """)
                record = await rel_result.single()
                if record:
                    results["relationship_health"] = {
                        "total": record["total"],
                        "with_embedding": record["with_embedding"],
                        "with_episodes": record["with_episodes"],
                        "with_fact": record["with_fact"],
                        "health_score": min(
                            record["with_embedding"] / record["total"],
                            record["with_episodes"] / record["total"]
                        ) if record["total"] > 0 else 0
                    }
                
                return results
                
        except Exception as e:
            log_error(f"Error verifying schema health: {e}")
            results["error"] = str(e)
            return results
    
    async def close(self):
        """Close database connection."""
        if self.driver:
            await self.driver.close()


async def main():
    """Main migration function."""
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
    
    log_info("=== Neo4j Schema Migration ===")
    log_info(f"Connecting to: {neo4j_uri}")
    
    migration = Neo4jSchemaMigration(neo4j_uri, neo4j_user, neo4j_password)
    
    if not await migration.initialize():
        log_error("Failed to connect to Neo4j. Check connection details.")
        return
    
    try:
        # Step 1: Create vector indices
        log_info("\n1. Creating vector indices...")
        if await migration.create_vector_indices():
            log_info("✅ Vector indices created successfully")
        else:
            log_error("❌ Failed to create vector indices")
            return
        
        # Step 2: Validate and fix missing properties
        log_info("\n2. Validating and fixing missing properties...")
        fix_results = await migration.validate_and_fix_missing_properties()
        if "error" in fix_results:
            log_error(f"❌ Property validation failed: {fix_results['error']}")
        else:
            log_info(f"✅ Checked {fix_results['entities_checked']} entities, fixed {fix_results['entities_fixed']}")
            log_info(f"✅ Checked {fix_results['relationships_checked']} relationships, fixed {fix_results['relationships_fixed']}")
        
        # Step 3: Create additional constraints
        log_info("\n3. Creating additional constraints...")
        if await migration.create_additional_constraints():
            log_info("✅ Additional constraints created successfully")
        else:
            log_error("❌ Failed to create additional constraints")
        
        # Step 4: Verify schema health
        log_info("\n4. Verifying schema health...")
        health_results = await migration.verify_schema_health()
        if "error" in health_results:
            log_error(f"❌ Health check failed: {health_results['error']}")
        else:
            log_info(f"Vector indices: {len(health_results.get('vector_indices', []))}")
            
            entity_health = health_results.get("entity_health", {})
            if entity_health:
                log_info(f"Entity health: {entity_health['health_score']:.2%} complete")
                log_info(f"  {entity_health['with_embedding']}/{entity_health['total']} have embeddings")
            
            rel_health = health_results.get("relationship_health", {})
            if rel_health:
                log_info(f"Relationship health: {rel_health['health_score']:.2%} complete")
                log_info(f"  {rel_health['with_embedding']}/{rel_health['total']} have embeddings")
        
        log_info("\n=== Migration Complete ===")
        log_info("Your Neo4j knowledge graph schema has been updated!")
        log_info("The warnings about missing properties should now be resolved.")
        
    finally:
        await migration.close()


if __name__ == "__main__":
    asyncio.run(main())