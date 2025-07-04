#!/usr/bin/env python3
"""Migration script to copy data from local Neo4j to Neo4j Aura cloud instance."""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from neo4j import GraphDatabase


def export_local_graph(local_uri: str, local_user: str, local_password: str) -> Dict[str, Any]:
    """Export all nodes and relationships from local Neo4j.
    
    Args:
        local_uri: Local Neo4j URI
        local_user: Local Neo4j username
        local_password: Local Neo4j password
        
    Returns:
        Dictionary with nodes and relationships
    """
    driver = GraphDatabase.driver(local_uri, auth=(local_user, local_password))
    
    export_data = {
        "nodes": [],
        "relationships": [],
        "metadata": {
            "export_timestamp": datetime.now().isoformat(),
            "source_uri": local_uri
        }
    }
    
    try:
        with driver.session() as session:
            # Export all nodes
            print("Exporting nodes...")
            nodes_query = """
            MATCH (n)
            RETURN id(n) as id, labels(n) as labels, properties(n) as properties
            """
            nodes_result = session.run(nodes_query)
            
            for record in nodes_result:
                node_data = {
                    "temp_id": record["id"],  # Temporary ID for relationship mapping
                    "labels": record["labels"],
                    "properties": record["properties"]
                }
                export_data["nodes"].append(node_data)
            
            print(f"Exported {len(export_data['nodes'])} nodes")
            
            # Export all relationships
            print("Exporting relationships...")
            rels_query = """
            MATCH (a)-[r]->(b)
            RETURN id(a) as from_id, id(b) as to_id, type(r) as type, properties(r) as properties
            """
            rels_result = session.run(rels_query)
            
            for record in rels_result:
                rel_data = {
                    "from_temp_id": record["from_id"],
                    "to_temp_id": record["to_id"],
                    "type": record["type"],
                    "properties": record["properties"]
                }
                export_data["relationships"].append(rel_data)
            
            print(f"Exported {len(export_data['relationships'])} relationships")
            
    finally:
        driver.close()
    
    return export_data


def import_to_cloud(cloud_uri: str, cloud_user: str, cloud_password: str, export_data: Dict[str, Any]) -> None:
    """Import nodes and relationships to Neo4j Aura.
    
    Args:
        cloud_uri: Neo4j Aura URI
        cloud_user: Neo4j Aura username
        cloud_password: Neo4j Aura password
        export_data: Exported graph data
    """
    driver = GraphDatabase.driver(cloud_uri, auth=(cloud_user, cloud_password), encrypted=True)
    
    try:
        with driver.session() as session:
            # Create a mapping from old IDs to new IDs
            id_mapping = {}
            
            # Import nodes
            print("Importing nodes to cloud...")
            for i, node in enumerate(export_data["nodes"]):
                # Build CREATE query with labels
                labels_str = ":".join(node["labels"]) if node["labels"] else "Node"
                
                # Create node and return its new ID
                query = f"""
                CREATE (n:{labels_str} $props)
                RETURN id(n) as new_id
                """
                
                result = session.run(query, props=node["properties"])
                record = result.single()
                
                if record:
                    id_mapping[node["temp_id"]] = record["new_id"]
                
                if (i + 1) % 100 == 0:
                    print(f"  Imported {i + 1}/{len(export_data['nodes'])} nodes...")
            
            print(f"Imported {len(export_data['nodes'])} nodes")
            
            # Import relationships
            print("Importing relationships to cloud...")
            for i, rel in enumerate(export_data["relationships"]):
                # Skip if we don't have mapped IDs
                if rel["from_temp_id"] not in id_mapping or rel["to_temp_id"] not in id_mapping:
                    print(f"  Warning: Skipping relationship due to missing node mapping")
                    continue
                
                # Use MATCH with internal IDs
                query = f"""
                MATCH (a) WHERE id(a) = $from_id
                MATCH (b) WHERE id(b) = $to_id
                CREATE (a)-[r:{rel["type"]} $props]->(b)
                RETURN r
                """
                
                params = {
                    "from_id": id_mapping[rel["from_temp_id"]],
                    "to_id": id_mapping[rel["to_temp_id"]],
                    "props": rel["properties"] or {}
                }
                
                session.run(query, params)
                
                if (i + 1) % 100 == 0:
                    print(f"  Imported {i + 1}/{len(export_data['relationships'])} relationships...")
            
            print(f"Imported {len(export_data['relationships'])} relationships")
            
            # Create indexes for better performance
            print("Creating indexes...")
            index_queries = [
                "CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)",
                "CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)",
                "CREATE INDEX document_id IF NOT EXISTS FOR (n:Document) ON (n.id)",
                "CREATE INDEX document_title IF NOT EXISTS FOR (n:Document) ON (n.title)"
            ]
            
            for index_query in index_queries:
                try:
                    session.run(index_query)
                except Exception as e:
                    print(f"  Warning: Index creation failed (may already exist): {str(e)}")
            
    finally:
        driver.close()


def verify_migration(cloud_uri: str, cloud_user: str, cloud_password: str) -> None:
    """Verify the migration by checking counts and sample data.
    
    Args:
        cloud_uri: Neo4j Aura URI
        cloud_user: Neo4j Aura username
        cloud_password: Neo4j Aura password
    """
    driver = GraphDatabase.driver(cloud_uri, auth=(cloud_user, cloud_password), encrypted=True)
    
    try:
        with driver.session() as session:
            # Get node count
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            print(f"\nVerification - Total nodes: {node_count}")
            
            # Get relationship count
            rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
            print(f"Verification - Total relationships: {rel_count}")
            
            # Get label distribution
            labels_result = session.run("""
                MATCH (n)
                UNWIND labels(n) as label
                RETURN label, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\nLabel distribution:")
            for record in labels_result:
                print(f"  {record['label']}: {record['count']}")
            
            # Get relationship type distribution
            rel_types_result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(*) as count
                ORDER BY count DESC
            """)
            
            print("\nRelationship type distribution:")
            for record in rel_types_result:
                print(f"  {record['type']}: {record['count']}")
                
    finally:
        driver.close()


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate Neo4j data to Neo4j Aura cloud instance")
    parser.add_argument("--env-file", default="local.env", help="Environment file path")
    parser.add_argument("--clear-target", action="store_true", help="Clear target database before import")
    parser.add_argument("--verify-only", action="store_true", help="Only verify the target database")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(args.env_file)
    
    # Get connection details
    # Local Neo4j (assuming different env vars for local)
    local_uri = os.getenv("NEO4J_LOCAL_URI", "bolt://localhost:7687")
    local_user = os.getenv("NEO4J_LOCAL_USER", "neo4j")
    local_password = os.getenv("NEO4J_LOCAL_PASSWORD", os.getenv("NEO4J_PASSWORD"))
    
    # Cloud Neo4j
    cloud_uri = os.getenv("NEO4J_URI")
    cloud_user = os.getenv("NEO4J_USER", "neo4j")
    cloud_password = os.getenv("NEO4J_PASSWORD")
    
    if not cloud_uri or not cloud_password:
        print("Error: NEO4J_URI and NEO4J_PASSWORD must be set for cloud instance")
        sys.exit(1)
    
    print(f"Migration Configuration:")
    print(f"  Source: {local_uri}")
    print(f"  Target: {cloud_uri}")
    
    if args.verify_only:
        print("\nVerifying cloud database...")
        verify_migration(cloud_uri, cloud_user, cloud_password)
        return
    
    # Clear target if requested
    if args.clear_target:
        print("\nClearing target database...")
        driver = GraphDatabase.driver(cloud_uri, auth=(cloud_user, cloud_password), encrypted=True)
        with driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        driver.close()
        print("Target database cleared")
    
    # Export from local
    print("\nExporting from local Neo4j...")
    export_data = export_local_graph(local_uri, local_user, local_password)
    
    # Import to cloud
    print("\nImporting to Neo4j Aura...")
    import_to_cloud(cloud_uri, cloud_user, cloud_password, export_data)
    
    # Verify
    print("\nVerifying migration...")
    verify_migration(cloud_uri, cloud_user, cloud_password)
    
    print("\nMigration complete!")


if __name__ == "__main__":
    main()