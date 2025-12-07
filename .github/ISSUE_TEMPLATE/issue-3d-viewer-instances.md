---
name: 3D Viewer - Fix Instance Rendering
about: BambuStudio 3MFs with multiple instances only show base geometry
title: '[BUG] 3D Viewer not rendering BambuStudio instances'
labels: 'quote-portal, bug, good first issue, ui/ux'
assignees: ''
---

## Problem
When a 3MF file contains multiple instances (e.g., 25 duck copies arranged via BambuStudio), only the base geometry renders in the 3D viewer, not the duplicate instances.

## To Reproduce
1. Start mock-api server: `cd mock-api && npm start`
2. Upload a 3MF with instances (create by arranging multiple copies in BambuStudio)
3. Observe that only 1 object renders instead of N instances

## Expected Behavior
All instances should render at their correct positions/rotations as stored in the 3MF metadata.

## Technical Details
- **File:** `src/components/ModelViewer.jsx` (in quote-portal repo)
- **Issue:** BambuStudio stores instance transforms in 3MF metadata
- **Solution:** Parse instance data and render multiple copies
- **Reference:** See `MULTI_MATERIAL_QUOTING.md` section on instance detection

## Environment
- Use `mock-api/` for testing (no full backend needed)
- The mock server correctly parses 3MF metadata
- This is purely a frontend rendering issue

## Additional Context
The mock API already extracts instance data - this is just about displaying it in the Three.js viewer.

## Help Wanted
This is a great first issue! You'll learn about:
- Three.js object instancing
- 3MF file format internals
- React component optimization
