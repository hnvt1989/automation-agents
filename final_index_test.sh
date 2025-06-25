#!/bin/bash
# Final test to index the specific file

echo "Final Index Test for dmt_release_process.md"
echo "==========================================="

# Show current working directory
echo "Current directory: $(pwd)"

# Check if file exists
echo -e "\n1. File check:"
ls -la data/va_notes/dmt_release_process.md

# Show file content
echo -e "\n2. File content (first 10 lines):"
head -10 data/va_notes/dmt_release_process.md

# Try indexing just this file with verbose output
echo -e "\n3. Indexing with --force flag:"
./index_docs.sh --force --directories data/va_notes --extensions .md 2>&1 | grep -E "(dmt_release|Indexing file:|Successfully indexed:|Failed:|Skipping)"

# Check if it's in the database now
echo -e "\n4. Checking database after indexing:"
python3 check_specific_doc.py 2>/dev/null || echo "Python check failed"

echo -e "\nDone."