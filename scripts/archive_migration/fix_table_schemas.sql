-- Fix missing doc_type column in notes, memos, and interviews tables
-- Run these commands in the Supabase SQL Editor

-- Add doc_type column to notes table
ALTER TABLE notes 
ADD COLUMN IF NOT EXISTS doc_type VARCHAR(50) NOT NULL DEFAULT 'note';

-- Add doc_type column to memos table  
ALTER TABLE memos
ADD COLUMN IF NOT EXISTS doc_type VARCHAR(50) NOT NULL DEFAULT 'memo';

-- Add doc_type column to interviews table
ALTER TABLE interviews
ADD COLUMN IF NOT EXISTS doc_type VARCHAR(50) NOT NULL DEFAULT 'interview';

-- Add missing indexes
CREATE INDEX IF NOT EXISTS idx_notes_doc_type ON notes(doc_type);
CREATE INDEX IF NOT EXISTS idx_memos_doc_type ON memos(doc_type);
CREATE INDEX IF NOT EXISTS idx_interviews_doc_type ON interviews(doc_type);

-- Verify the changes
SELECT 'notes' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'notes' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 'memos' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'memos' AND table_schema = 'public'
ORDER BY ordinal_position;

SELECT 'interviews' as table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'interviews' AND table_schema = 'public'
ORDER BY ordinal_position;