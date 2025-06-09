# TODO: Modal System Migration

## Gradual Migration from HTML Editor to React Modal System

### Phase 1: Extend React TaskModal
- [ ] Extend React TaskModal to handle all content types (tasks, documents, notes, logs)
- [ ] Add type-specific field rendering based on content type
- [ ] Implement content field for documents/notes (large text areas)
- [ ] Add log-specific fields (date, hours)
- [ ] Implement read-only field behavior for certain types
- [ ] Add type-specific validation and behavior

### Phase 2: Create Specialized Modal Components
- [ ] Create DocumentModal component extending base modal functionality
- [ ] Create NoteModal component with content editing capabilities
- [ ] Create LogModal component with date/hours fields
- [ ] Maintain TaskModal as-is (already complete with Log button functionality)
- [ ] Ensure consistent styling and behavior across all modals

### Phase 3: Implement Advanced Features
- [ ] Add Index button functionality for documents/notes (AI file indexing)
- [ ] Implement proper content management for documents/notes
- [ ] Add bulk operations support across all modal types
- [ ] Ensure proper error handling and validation

### Phase 4: Integration and State Management
- [ ] Update WorkspaceContent to route different types to appropriate modals
- [ ] Ensure proper state management integration with useAppStore
- [ ] Update API hooks to work consistently across all content types
- [ ] Add proper loading states and error handling

### Phase 5: Switch Routing and Remove HTML Editor
- [ ] Update TasksTab, DocumentsTab, NotesTab, LogsTab to use React modals
- [ ] Replace HTML Editor calls with React modal setModal calls
- [ ] Update Panel component in index.html to remove Editor usage
- [ ] Remove HTML Editor component entirely
- [ ] Clean up unused CSS and HTML code

### Phase 6: Testing and Validation
- [ ] Test all content types with new modal system
- [ ] Verify all existing functionality works (create, edit, delete)
- [ ] Test Log button functionality across the system
- [ ] Ensure proper form validation and error handling
- [ ] Test modal responsiveness and accessibility

### Benefits of This Migration:
- ✅ Cleaner architecture with better maintainability
- ✅ Consistent React component patterns
- ✅ Better type safety with TypeScript
- ✅ Improved testing capabilities
- ✅ Unified state management
- ✅ Better separation of concerns

### Risk Mitigation:
- Keep both systems during transition
- Phase-by-phase implementation to catch issues early
- Maintain backward compatibility until full migration
- Thorough testing at each phase 