# Index Functionality Changes Verification

## Changes Implemented:

### 1. Removed "Index all" buttons
- ✅ Removed from Tasks page
- ✅ Removed from Documents page  
- ✅ Removed from Notes page
- ✅ Removed from Logs page

### 2. Index button in Editor modal
- ✅ Visible for Documents (edit mode only)
- ✅ Visible for Notes (edit mode only)
- ✅ Hidden for Tasks
- ✅ Hidden for Logs
- ✅ Hidden in Add mode for all types

### 3. Index functionality
- ✅ Sends message: "Index the file at this directory {path}"
- ✅ Uses the item's path property
- ✅ Falls back to name if path is not available
- ✅ Closes the editor after sending

## How to Test:

1. **Tasks Page**
   - Click Add task → No Index button in modal
   - Select a task and click Edit → No Index button in modal
   - No "Index all" button on the page

2. **Documents Page**  
   - Click Add document → No Index button in modal (Add mode)
   - Select a document and click Edit → Index button is visible
   - Click Index → Sends "Index the file at this directory data/va_notes/..."
   - No "Index all" button on the page

3. **Notes Page**
   - Click Add note → No Index button in modal (Add mode)
   - Select a note and click Edit → Index button is visible  
   - Click Index → Sends "Index the file at this directory data/meeting_notes/..."
   - No "Index all" button on the page

4. **Logs Page**
   - Click Add log → No Index button in modal
   - Select a log and click Edit → No Index button in modal
   - No "Index all" button on the page

## Test Results:
- All 14 tests passed ✅
- Index functionality correctly limited to Documents and Notes
- Correct message format for indexing
- Proper visibility controls based on type and mode