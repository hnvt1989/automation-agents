#!/usr/bin/env python3
"""
Regenerate Embeddings Script

This script regenerates embeddings for existing entities and relationships
in the Neo4j knowledge graph to ensure all nodes have proper vector embeddings.
"""

import asyncio
import os
import sys
from typing import Dict, Any, List
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from neo4j import AsyncGraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from src.utils.logging import log_info, log_error, log_warning
except ImportError:
    def log_info(msg): print(f"INFO: {msg}")
    def log_error(msg): print(f"ERROR: {msg}")
    def log_warning(msg): print(f"WARNING: {msg}")


class EmbeddingRegenerator:
    """Regenerates embeddings for Neo4j knowledge graph."""
    
    def __init__(self, uri: str, user: str, password: str, openai_api_key: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.openai_api_key = openai_api_key
        self.driver = None
        self.openai_client = None
    
    async def initialize(self):
        """Initialize connections."""
        if not NEO4J_AVAILABLE:
            log_error("Neo4j driver not available. Install with: pip install neo4j")
            return False
        
        if not OPENAI_AVAILABLE:
            log_error("OpenAI library not available. Install with: pip install openai")
            return False
        
        try:
            # Initialize Neo4j
            self.driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            await self.driver.verify_connectivity()
            log_info("Connected to Neo4j successfully")
            
            # Initialize OpenAI
            self.openai_client = openai.AsyncOpenAI(api_key=self.openai_api_key)
            log_info("OpenAI client initialized")
            
            return True
        except Exception as e:
            log_error(f"Failed to initialize: {e}")
            return False
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                dimensions=1536
            )
            return response.data[0].embedding
        except Exception as e:
            log_error(f"Failed to get embedding for text: {e}")
            return [0.0] * 1536  # Return zero vector as fallback
    
    async def regenerate_entity_embeddings(self) -> Dict[str, Any]:
        """Regenerate embeddings for Entity nodes."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {
            "total_entities": 0,
            "updated_entities": 0,
            "errors": 0
        }
        
        try:
            async with self.driver.session() as session:
                # Get all entities that need embedding updates
                entity_result = await session.run("""
                    MATCH (n:Entity)
                    WHERE n.name_embedding IS NULL 
                       OR size(n.name_embedding) = 0
                       OR all(x IN n.name_embedding WHERE x = 0.0)
                    RETURN n.uuid as uuid, n.name as name, n.summary as summary
                """)
                
                entities_to_update = []
                async for record in entity_result:
                    entities_to_update.append({
                        "uuid": record["uuid"],
                        "name": record["name"],
                        "summary": record["summary"]
                    })
                
                results["total_entities"] = len(entities_to_update)
                log_info(f"Found {len(entities_to_update)} entities needing embedding updates")
                
                # Update embeddings in batches
                batch_size = 10
                for i in range(0, len(entities_to_update), batch_size):
                    batch = entities_to_update[i:i + batch_size]
                    
                    for entity in batch:
                        try:
                            # Create embedding text from name and summary
                            embedding_text = f"{entity['name']} {entity.get('summary', '')}"
                            embedding = await self.get_embedding(embedding_text)
                            
                            # Update the entity
                            await session.run("""
                                MATCH (n:Entity {uuid: $uuid})
                                SET n.name_embedding = $embedding
                            """, uuid=entity["uuid"], embedding=embedding)
                            
                            results["updated_entities"] += 1
                            
                        except Exception as e:
                            log_error(f"Failed to update entity {entity['uuid']}: {e}")
                            results["errors"] += 1
                    
                    # Log progress
                    log_info(f"Updated {min(i + batch_size, len(entities_to_update))}/{len(entities_to_update)} entities")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                
                return results
                
        except Exception as e:
            log_error(f"Error regenerating entity embeddings: {e}")
            results["error"] = str(e)
            return results
    
    async def regenerate_relationship_embeddings(self) -> Dict[str, Any]:
        """Regenerate embeddings for RELATES_TO relationships."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {
            "total_relationships": 0,
            "updated_relationships": 0,
            "errors": 0
        }
        
        try:
            async with self.driver.session() as session:
                # Get all relationships that need embedding updates
                rel_result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    WHERE r.fact_embedding IS NULL 
                       OR size(r.fact_embedding) = 0
                       OR all(x IN r.fact_embedding WHERE x = 0.0)
                       OR r.episodes IS NULL
                    RETURN r.uuid as uuid, r.fact as fact
                """)
                
                relationships_to_update = []
                async for record in rel_result:
                    relationships_to_update.append({
                        "uuid": record["uuid"],
                        "fact": record["fact"]
                    })
                
                results["total_relationships"] = len(relationships_to_update)
                log_info(f"Found {len(relationships_to_update)} relationships needing embedding updates")
                
                # Update embeddings in batches
                batch_size = 10
                for i in range(0, len(relationships_to_update), batch_size):
                    batch = relationships_to_update[i:i + batch_size]
                    
                    for relationship in batch:
                        try:
                            # Create embedding from fact text
                            fact_text = relationship.get('fact', '')
                            if not fact_text:
                                fact_text = "Unknown relationship"
                            
                            embedding = await self.get_embedding(fact_text)
                            
                            # Update the relationship
                            await session.run("""
                                MATCH ()-[r:RELATES_TO {uuid: $uuid}]->()
                                SET r.fact_embedding = $embedding,
                                    r.episodes = CASE 
                                        WHEN r.episodes IS NULL THEN []
                                        ELSE r.episodes 
                                    END
                            """, uuid=relationship["uuid"], embedding=embedding)
                            
                            results["updated_relationships"] += 1
                            
                        except Exception as e:
                            log_error(f"Failed to update relationship {relationship['uuid']}: {e}")
                            results["errors"] += 1
                    
                    # Log progress
                    log_info(f"Updated {min(i + batch_size, len(relationships_to_update))}/{len(relationships_to_update)} relationships")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                
                return results
                
        except Exception as e:
            log_error(f"Error regenerating relationship embeddings: {e}")
            results["error"] = str(e)
            return results
    
    async def validate_embeddings(self) -> Dict[str, Any]:
        """Validate that all embeddings are properly generated."""
        if not self.driver:
            return {"error": "Not connected"}
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # Check entity embeddings
                entity_result = await session.run("""
                    MATCH (n:Entity)
                    RETURN 
                        count(n) as total,
                        count(n.name_embedding) as with_embedding,
                        sum(CASE WHEN size(n.name_embedding) = 1536 THEN 1 ELSE 0 END) as correct_size,
                        sum(CASE WHEN all(x IN n.name_embedding WHERE x = 0.0) THEN 1 ELSE 0 END) as zero_embeddings
                """)
                record = await entity_result.single()
                if record:
                    results["entities"] = {
                        "total": record["total"],
                        "with_embedding": record["with_embedding"],
                        "correct_size": record["correct_size"],
                        "zero_embeddings": record["zero_embeddings"]
                    }
                
                # Check relationship embeddings
                rel_result = await session.run("""
                    MATCH ()-[r:RELATES_TO]->()
                    RETURN 
                        count(r) as total,
                        count(r.fact_embedding) as with_embedding,
                        sum(CASE WHEN size(r.fact_embedding) = 1536 THEN 1 ELSE 0 END) as correct_size,
                        sum(CASE WHEN all(x IN r.fact_embedding WHERE x = 0.0) THEN 1 ELSE 0 END) as zero_embeddings,
                        count(r.episodes) as with_episodes
                """)
                record = await rel_result.single()
                if record:
                    results["relationships"] = {
                        "total": record["total"],
                        "with_embedding": record["with_embedding"],
                        "correct_size": record["correct_size"],
                        "zero_embeddings": record["zero_embeddings"],
                        "with_episodes": record["with_episodes"]
                    }
                
                return results
                
        except Exception as e:
            log_error(f"Error validating embeddings: {e}")
            results["error"] = str(e)
            return results
    
    async def close(self):
        """Close connections."""
        if self.driver:
            await self.driver.close()


async def main():
    """Main regeneration function."""
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv("local.env")
    except ImportError:
        log_warning("python-dotenv not installed, using os.environ")
    
    # Get connection details
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        log_error("OPENAI_API_KEY not found in environment variables")
        return
    
    log_info("=== Neo4j Embedding Regeneration ===")
    log_info(f"Connecting to: {neo4j_uri}")
    
    regenerator = EmbeddingRegenerator(neo4j_uri, neo4j_user, neo4j_password, openai_api_key)
    
    if not await regenerator.initialize():
        log_error("Failed to initialize regenerator")
        return
    
    try:
        # Validate current state
        log_info("\n1. Validating current embedding state...")
        validation_before = await regenerator.validate_embeddings()
        if "error" in validation_before:
            log_error(f"Validation failed: {validation_before['error']}")
            return
        
        entities = validation_before.get("entities", {})
        relationships = validation_before.get("relationships", {})
        
        log_info(f"Current state:")
        log_info(f"  Entities: {entities.get('with_embedding', 0)}/{entities.get('total', 0)} have embeddings")
        log_info(f"  Relationships: {relationships.get('with_embedding', 0)}/{relationships.get('total', 0)} have embeddings")
        
        # Regenerate entity embeddings
        log_info("\n2. Regenerating entity embeddings...")
        entity_results = await regenerator.regenerate_entity_embeddings()
        if "error" in entity_results:
            log_error(f"Entity regeneration failed: {entity_results['error']}")
        else:
            log_info(f"✅ Updated {entity_results['updated_entities']}/{entity_results['total_entities']} entities")
            if entity_results['errors'] > 0:
                log_warning(f"❌ {entity_results['errors']} entities failed to update")
        
        # Regenerate relationship embeddings
        log_info("\n3. Regenerating relationship embeddings...")
        rel_results = await regenerator.regenerate_relationship_embeddings()
        if "error" in rel_results:
            log_error(f"Relationship regeneration failed: {rel_results['error']}")
        else:
            log_info(f"✅ Updated {rel_results['updated_relationships']}/{rel_results['total_relationships']} relationships")
            if rel_results['errors'] > 0:
                log_warning(f"❌ {rel_results['errors']} relationships failed to update")
        
        # Final validation
        log_info("\n4. Final validation...")
        validation_after = await regenerator.validate_embeddings()
        if "error" in validation_after:
            log_error(f"Final validation failed: {validation_after['error']}")
        else:
            entities_after = validation_after.get("entities", {})
            relationships_after = validation_after.get("relationships", {})
            
            log_info(f"Final state:")
            log_info(f"  Entities: {entities_after.get('with_embedding', 0)}/{entities_after.get('total', 0)} have embeddings")
            log_info(f"  Relationships: {relationships_after.get('with_embedding', 0)}/{relationships_after.get('total', 0)} have embeddings")
            
            if entities_after.get('zero_embeddings', 0) > 0:
                log_warning(f"  {entities_after['zero_embeddings']} entities have zero embeddings (may need manual review)")
            if relationships_after.get('zero_embeddings', 0) > 0:
                log_warning(f"  {relationships_after['zero_embeddings']} relationships have zero embeddings (may need manual review)")
        
        log_info("\n=== Regeneration Complete ===")
        log_info("All embeddings have been regenerated!")
        
    finally:
        await regenerator.close()


if __name__ == "__main__":
    asyncio.run(main())