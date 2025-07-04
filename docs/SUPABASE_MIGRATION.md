# Supabase Migration Guide

This guide explains how to migrate your tasks and daily logs from YAML files to a hosted Supabase database.

## Overview

The migration moves data from:
- `data/tasks.yaml` → Supabase `tasks` table
- `data/daily_logs.yaml` → Supabase `daily_logs` table

## Prerequisites

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Get your project URL and anon key from the Supabase dashboard

## Setup Steps

### 1. Configure Environment Variables

Copy the example environment file and add your Supabase credentials:

```bash
cp local.env.example local.env
```

Edit `local.env` and add:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

### 2. Install Dependencies

Make sure you have the latest dependencies:

```bash
pip install -r requirements.txt
```

### 3. Create Database Schema

In your Supabase dashboard, go to the SQL Editor and run the schema script:

```bash
# The schema is in scripts/supabase_schema.sql
```

Copy and paste the contents of `scripts/supabase_schema.sql` into the Supabase SQL editor and execute it.

### 4. Migrate Existing Data

Run the migration script to transfer your YAML data to Supabase:

```bash
# Dry run first (no data will be inserted)
python scripts/migrate_to_supabase.py --dry-run

# Run the actual migration
python scripts/migrate_to_supabase.py

# Verify the migration
python scripts/migrate_to_supabase.py --verify-only
```

### 5. Run the Application

Use the new Supabase-backed API server:

```bash
# Using the convenience script
./run_supabase.sh

# Or directly with uvicorn
python -m uvicorn src.api_server_supabase:app --reload
```

## Features

### Database Schema

**Tasks Table:**
- `id` - Unique task identifier
- `title` - Task title
- `description` - Task description
- `status` - pending, in_progress, completed, cancelled
- `priority` - low, medium, high
- `due_date` - Due date
- `tags` - Array of tags
- `estimate_hours` - Estimated hours
- `todo` - TODO items/notes
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

**Daily Logs Table:**
- `id` - Auto-incrementing ID
- `log_date` - Date of the log
- `log_id` - Log identifier
- `description` - Log description
- `actual_hours` - Hours worked
- `task_id` - Optional link to task
- `created_at` - Creation timestamp
- `updated_at` - Last update timestamp

### Benefits of Supabase

1. **Real-time Sync** - Access your data from anywhere
2. **Concurrent Access** - Multiple users can work simultaneously
3. **Automatic Backups** - Supabase handles backups
4. **Scalability** - Handles large amounts of data efficiently
5. **Security** - Row Level Security (RLS) support
6. **Real-time Subscriptions** - Future support for live updates

## API Compatibility

The Supabase-backed API maintains full compatibility with the existing frontend. All endpoints work the same way:

- `GET /tasks` - Get all tasks
- `POST /tasks` - Create a new task
- `PUT /tasks/{id}` - Update a task
- `DELETE /tasks/{id}` - Delete a task
- `GET /logs` - Get all logs
- `POST /logs` - Create a new log
- `PUT /logs/{index}` - Update a log
- `DELETE /logs/{index}` - Delete a log

## Rollback

If you need to switch back to YAML files:

1. Stop the Supabase API server
2. Run the original API server:
   ```bash
   python -m uvicorn src.api_server:app --reload
   ```

Your YAML files remain untouched during migration, so you can always go back.

## Troubleshooting

### Connection Issues
- Verify your `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check your internet connection
- Ensure your Supabase project is active

### Migration Errors
- Run with `--dry-run` first to preview changes
- Check logs for specific error messages
- Verify the database schema was created correctly

### Performance
- Add appropriate indexes for your queries
- Use the Supabase dashboard to monitor performance
- Consider caching for frequently accessed data

## Next Steps

1. Set up Row Level Security (RLS) for multi-user support
2. Enable real-time subscriptions for live updates
3. Add user authentication
4. Set up automated backups
5. Monitor usage and optimize queries