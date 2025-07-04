#!/usr/bin/env python3
"""
Migration script to transfer existing YAML data to Supabase database.

Usage:
    python scripts/migrate_to_supabase.py [--dry-run]
"""

import sys
import os
import yaml
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from src.storage.supabase_client import get_supabase_client
from src.utils.logging import log_info, log_error, log_warning


def load_yaml_file(file_path: str) -> any:
    """Load data from a YAML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or []
    except FileNotFoundError:
        log_warning(f"File not found: {file_path}")
        return []
    except Exception as e:
        log_error(f"Error loading {file_path}: {str(e)}")
        return []


def migrate_tasks(dry_run: bool = False):
    """Migrate tasks from YAML to Supabase."""
    log_info("Starting tasks migration...")
    
    tasks_file = "data/tasks.yaml"
    tasks = load_yaml_file(tasks_file)
    
    if not tasks:
        log_warning("No tasks found to migrate")
        return
    
    log_info(f"Found {len(tasks)} tasks to migrate")
    
    if dry_run:
        log_info("DRY RUN - No data will be inserted")
        for task in tasks:
            log_info(f"Would migrate task: {task.get('id')} - {task.get('title')}")
        return
    
    # Get Supabase client
    client = get_supabase_client()
    tasks_table = client.get_tasks_table()
    
    success_count = 0
    error_count = 0
    
    for task in tasks:
        try:
            # Check if task already exists
            existing = tasks_table.select("*").eq("id", task["id"]).execute()
            
            if existing.data:
                log_warning(f"Task {task['id']} already exists, skipping")
                continue
            
            # Prepare task data
            task_data = {
                "id": task["id"],
                "title": task.get("title", "Untitled"),
                "description": task.get("description"),
                "status": task.get("status", "pending"),
                "priority": task.get("priority", "medium"),
                "due_date": task.get("due_date"),
                "tags": task.get("tags", []),
                "estimate_hours": task.get("estimate_hours"),
                "todo": task.get("todo")
            }
            
            # Insert into Supabase
            result = tasks_table.insert(task_data).execute()
            
            if result.data:
                success_count += 1
                log_info(f"✓ Migrated task: {task['id']} - {task.get('title')}")
            else:
                error_count += 1
                log_error(f"✗ Failed to migrate task: {task['id']}")
                
        except Exception as e:
            error_count += 1
            log_error(f"✗ Error migrating task {task.get('id')}: {str(e)}")
    
    log_info(f"\nTasks migration complete: {success_count} success, {error_count} errors")


def migrate_daily_logs(dry_run: bool = False):
    """Migrate daily logs from YAML to Supabase."""
    log_info("\nStarting daily logs migration...")
    
    logs_file = "data/daily_logs.yaml"
    logs_data = load_yaml_file(logs_file)
    
    if not logs_data:
        log_warning("No daily logs found to migrate")
        return
    
    # Count total logs
    total_logs = sum(len(logs) for logs in logs_data.values() if logs)
    log_info(f"Found {total_logs} log entries across {len(logs_data)} dates")
    
    if dry_run:
        log_info("DRY RUN - No data will be inserted")
        for date, logs in logs_data.items():
            if logs:
                for log in logs:
                    log_info(f"Would migrate log: {date} - {log.get('log_id')} - {log.get('description')[:50]}...")
        return
    
    # Get Supabase client
    client = get_supabase_client()
    logs_table = client.get_logs_table()
    
    success_count = 0
    error_count = 0
    
    for date, daily_logs in logs_data.items():
        if not daily_logs:
            continue
            
        for log in daily_logs:
            try:
                # Prepare log data
                log_data = {
                    "log_date": str(date),  # Ensure date is string
                    "log_id": log.get("log_id", f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                    "description": log.get("description", ""),
                    "actual_hours": float(log.get("actual_hours", 0))
                }
                
                # Try to match with task_id if log_id matches a task
                if log_data["log_id"].startswith("TASK-") or log_data["log_id"].startswith("ONBOARDING-"):
                    log_data["task_id"] = log_data["log_id"]
                
                # Insert into Supabase
                result = logs_table.insert(log_data).execute()
                
                if result.data:
                    success_count += 1
                    log_info(f"✓ Migrated log: {date} - {log.get('log_id')}")
                else:
                    error_count += 1
                    log_error(f"✗ Failed to migrate log: {date} - {log.get('log_id')}")
                    
            except Exception as e:
                error_count += 1
                log_error(f"✗ Error migrating log {log.get('log_id')} for {date}: {str(e)}")
    
    log_info(f"\nDaily logs migration complete: {success_count} success, {error_count} errors")


def verify_migration():
    """Verify the migration by comparing counts."""
    log_info("\nVerifying migration...")
    
    # Load YAML data
    tasks_yaml = load_yaml_file("data/tasks.yaml")
    logs_yaml = load_yaml_file("data/daily_logs.yaml")
    
    yaml_task_count = len(tasks_yaml) if tasks_yaml else 0
    yaml_log_count = sum(len(logs) for logs in logs_yaml.values() if logs) if logs_yaml else 0
    
    # Get Supabase counts
    client = get_supabase_client()
    
    try:
        db_tasks = client.get_tasks_table().select("*", count="exact").execute()
        db_task_count = db_tasks.count if db_tasks else 0
        
        db_logs = client.get_logs_table().select("*", count="exact").execute()
        db_log_count = db_logs.count if db_logs else 0
        
        log_info(f"\nMigration verification:")
        log_info(f"Tasks - YAML: {yaml_task_count}, Database: {db_task_count}")
        log_info(f"Logs - YAML: {yaml_log_count}, Database: {db_log_count}")
        
        if yaml_task_count == db_task_count and yaml_log_count == db_log_count:
            log_info("✓ Migration verified successfully!")
        else:
            log_warning("⚠ Counts don't match. Some items may have been skipped or failed.")
            
    except Exception as e:
        log_error(f"Error verifying migration: {str(e)}")


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate YAML data to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Run without inserting data")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing migration")
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv("local.env")
    
    # Check for required environment variables
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        log_error("SUPABASE_URL and SUPABASE_KEY must be set in local.env")
        sys.exit(1)
    
    if args.verify_only:
        verify_migration()
        return
    
    log_info("Starting YAML to Supabase migration...")
    log_info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    
    # Migrate tasks
    migrate_tasks(dry_run=args.dry_run)
    
    # Migrate daily logs
    migrate_daily_logs(dry_run=args.dry_run)
    
    # Verify migration if not dry run
    if not args.dry_run:
        verify_migration()
    
    log_info("\nMigration process complete!")


if __name__ == "__main__":
    main()