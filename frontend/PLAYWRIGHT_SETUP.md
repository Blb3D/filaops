# Playwright E2E Testing Setup

## ✅ Setup Complete

### Files Created/Updated

1. **`playwright.config.js`** - Playwright configuration (JavaScript)
   - Test directory: `./tests`
   - Base URL: `http://localhost:5173` (or `E2E_BASE_URL` env var)
   - Timeout: 60s
   - Trace/video/screenshots on failure

2. **`tests/scheduler.spec.js`** - Scheduler smoke tests (JavaScript)
   - Tests API error handling (500 errors show toast)
   - Tests drag-and-drop scheduling workflow
   - Validates schedule API payload

3. **Component Test Selectors Added**
   - `DraggableOrder`: `data-testid="order-{order.id}"`
   - `DroppableSlot`: `data-testid="slot-{machineId}-{slotIndex}"`

4. **`.github/workflows/e2e.yml`** - CI workflow (optional)
   - Runs on PRs to main/master
   - Installs dependencies, builds, runs tests

### Installation

Playwright is already installed. If you need to reinstall:

```bash
cd frontend
npm i -D @playwright/test
npx playwright install
```

### Running Tests

```bash
# Run all tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run only scheduler smoke tests
npm run test:smoke

# Run in headed mode (see browser)
npm run test:headed

# Debug mode
npm run test:e2e:debug
```

### Test Requirements

For the drag-and-drop test to work, you need:

1. **Unscheduled orders** in the sidebar with `data-testid="order-{id}"`
2. **Droppable slots** with `data-testid="slot-{machineId}-{slotIndex}"`
3. **Mock API responses** for work centers and resources
4. **Toast notifications** for success/error states

### Environment Variables

- `E2E_BASE_URL` - Override base URL (default: `http://localhost:5173`)
- `E2E_PAGE_PATH` - Override page path (default: `/admin/production`)

### CI/CD

The GitHub Actions workflow will:
1. Install dependencies
2. Install Playwright browsers
3. Build the app
4. Start dev server
5. Run E2E tests

### Next Steps

1. Ensure your dev server is running on port 5173 (or update `E2E_BASE_URL`)
2. Run `npm run test:e2e:ui` to see tests in action
3. Add more test cases as needed
4. Update test selectors if component structure changes

