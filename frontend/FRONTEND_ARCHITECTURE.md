# Frontend Architecture Warning

⚠️ **IMPORTANT**: This project currently has TWO frontend implementations:

## Active Frontend (Currently Running)
- **File**: `index.html`
- **Technology**: Inline React with Babel transpilation
- **URL**: http://localhost:3000
- **Status**: ✅ Active and functional

## Inactive Frontend (Not Used)
- **Directory**: `src/`
- **Technology**: TypeScript + Vite + React
- **Status**: ❌ Not running, changes here won't be visible

## For Developers

### Making Changes
- ✅ **Edit**: `index.html` for UI changes
- ❌ **Don't Edit**: Files in `src/` directory

### Future Cleanup Options
1. **Keep HTML**: Remove `src/` directory entirely
2. **Migrate to TypeScript**: Remove `index.html` and use `src/` properly
3. **Hybrid**: Keep both but document clearly

### Tests
- Tests in `tests/` directory reference the `src/` components
- These tests will fail because they test unused code
- Tests need to be updated to test the actual HTML implementation

## Recent Changes
- Date picker functionality was added to `index.html` (correct location)
- Previous attempts to modify `src/components/Workspace/tabs/LogsTab.tsx` were ineffective