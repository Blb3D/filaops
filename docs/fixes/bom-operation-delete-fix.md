# BOM Operation Delete Fix

## Issue Description
Users reported being unable to remove operations from BOM routings after they were saved. The only available workaround was to delete the entire routing and recreate it from scratch.

**GitHub Issue**: User unable to remove an operation on a BOM

## Solution Overview
Added delete functionality for saved routing operations in the BOM UI.

## What Changed

### Before
- ✅ Could remove **pending** operations (not yet saved)
- ❌ Could NOT remove **saved** operations
- ❌ Only workaround: Delete entire routing and recreate

### After
- ✅ Can remove **pending** operations (unchanged)
- ✅ Can remove **saved** operations (NEW)
- ✅ Individual operation management

## Implementation Details

### 1. Delete Handler Function
Added `handleDeleteOperation` function that:
- Shows confirmation dialog before deletion
- Calls backend API: `DELETE /api/v1/routings/operations/{operation_id}`
- Refreshes routing data after successful deletion
- Displays appropriate toast notifications

### 2. Actions Column
- Added "Actions" column to operations table header
- Center-aligned for action buttons

### 3. Remove Button
- Red color to indicate destructive action
- Hover effects for better UX
- Tooltip on hover
- Confirmation required before deletion

## User Flow

1. User clicks "Remove" on an operation
2. Confirmation dialog appears: "Are you sure you want to remove operation '{name}'? This action cannot be undone."
3. On confirmation:
   - API call: `DELETE /api/v1/routings/operations/{operation_id}`
   - Success toast: "Operation removed successfully"
   - Routing data refreshes automatically
   - Operation disappears from table
   - Costs and times recalculate
4. On cancellation:
   - No action taken
   - Dialog closes

## Technical Details

### API Endpoint
- **Method**: DELETE
- **Path**: `/api/v1/routings/operations/{operation_id}`
- **Response**: 204 No Content
- **Behavior**: Soft delete (sets `is_active = False`)
- **Side Effects**: Recalculates routing totals

### Files Modified
- `frontend/src/pages/admin/AdminBOM.jsx`
  - Added `handleDeleteOperation()` function
  - Added "Actions" column to table header
  - Added Remove button in table rows

## Benefits

### For Users
✅ Can remove individual operations without recreating entire routing  
✅ Clear confirmation prevents accidental deletions  
✅ Immediate feedback through toast notifications  
✅ No page reload required - auto refresh  

### For Development
✅ Consistent with existing delete patterns in codebase  
✅ Uses existing backend API (no backend changes needed)  
✅ Follows established error handling patterns  
✅ Clean, maintainable code  

## Testing Recommendations

1. **Basic deletion**: Delete a single operation and verify it's removed
2. **Cancel**: Click Remove, then Cancel in dialog - verify no deletion
3. **Multiple deletions**: Delete several operations sequentially
4. **Error handling**: Test with network offline to see error handling
5. **UI verification**: Verify Actions column and Remove buttons display correctly
6. **Regression**: Verify editing run times still works

## Future Enhancements
1. Undo functionality for accidental deletions
2. Bulk delete multiple operations
3. Drag-and-drop resequencing
4. Apply same pattern to RoutingEditor component


