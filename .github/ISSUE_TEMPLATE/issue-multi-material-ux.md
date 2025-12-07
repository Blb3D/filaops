---
name: Multi-Material Color Selection UX
about: Improve the interface for selecting materials for each color slot
title: '[ENHANCEMENT] Better multi-material color selection UX'
labels: 'quote-portal, enhancement, help wanted, ui/ux'
assignees: ''
---

## Current Behavior
Users must select a material for each detected color slot, but the UI doesn't clearly show:
- Which colors are used where in the model
- How material choices affect the total price
- Preview of what the final print will look like

## Desired Improvements

### 1. Visual Color Mapping
- [ ] Color swatches should show a preview of where that color appears in the model
- [ ] Highlight the selected color in the 3D viewer
- [ ] Show percentage/weight breakdown per color

### 2. Real-time Cost Feedback
- [ ] Update price as user changes materials
- [ ] Show cost breakdown per material
- [ ] Indicate which material choices are most economical

### 3. Mobile Experience
- [ ] Better touch targets for color selection
- [ ] Collapsible material picker for small screens
- [ ] Swipe gestures for cycling through colors

### 4. Smart Defaults
- [ ] Auto-suggest materials based on common color combinations
- [ ] Remember user's previous material choices
- [ ] "Use same material for all colors" quick option

## Technical Details
- **Files:** `src/pages/GetQuote.jsx`, `src/pages/QuoteResult.jsx`
- **API:** Mock server returns correct color slots (see `mock-api/README.md`)
- **Reference:** `MULTI_MATERIAL_QUOTING.md` for color detection logic

## Environment
Test using the mock API server:
```bash
cd mock-api
npm install
npm start
```

Upload any multi-color 3MF from BambuStudio - the color detection works correctly, just needs better UI!

## Mockups/Examples
Screenshots or wireframes welcome! Let's make this the best multi-material quoting UX in the industry.

## Help Wanted
Great project for UI/UX designers and React developers. Skills you'll practice:
- React state management
- Three.js viewer integration
- Responsive design patterns
- User-centered design
