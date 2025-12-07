# FilaOps Quote Portal - Mock API Server

This mock server lets you develop the Quote Portal frontend **without the real backend stack**.

## Quick Start

```bash
npm install
npm start
```

The server runs on **two ports** to match production architecture:
- `http://localhost:8001` - ML API (slicer/quotes)
- `http://localhost:8000` - ERP API (materials/customers)

## What's Real vs Fake

### ✅ REAL (parsed from your actual files)

| Feature | How It Works |
|---------|--------------|
| **Material slot detection** | Scans mesh XML for `paint_color` attributes |
| **Color extraction** | Reads BambuStudio plate JSON and project settings |
| **Thumbnail extraction** | Pulls `Metadata/plate_1.png` from 3MF |
| **File format handling** | Real ZIP/XML parsing with JSZip |

When you upload a 3-color 3MF, it will correctly detect 3 colors.

### ❌ FAKE (generated/mocked)

| Feature | Mock Behavior | Real Backend |
|---------|---------------|--------------|
| **Material weights** | Random 50-250g, split proportionally | G-code header parsing |
| **Print times** | ~3 min per gram + 30 min per color | ML-corrected estimates |
| **Pricing** | $0.05-0.08/g × 1.5 for multi-color | Real cost formulas |
| **Slicing** | None - just delays 1 second | BambuStudio CLI |
| **Customer auth** | Always succeeds | Real validation |
| **Payment** | Redirects to success page | Stripe integration |

## Console Output

When you upload a file, you'll see parsing logs:

```
[3MF Parser] Parsing: MyModel
[3MF Parser] Extracted thumbnail: Metadata/plate_1.png
[3MF Parser] Found plate config: Metadata/plate_1.json
[3MF Parser] Found paint_color extruders in mesh: [ 0, 4, 8 ]
[3MF Parser] Multi-material detected: 3 materials
[3MF Parser] Colors: [ '#FF6B00', '#00FF00', '#FF0000' ]
```

## How 3MF Parsing Works

BambuStudio 3MFs can store multi-material info in several places:

1. **Plate JSON** (`Metadata/plate_1.json`)
   - `filament_ids` - which slots are used
   - `filament_colours` - hex colors per slot
   - `ams_mapping` - AMS slot assignments

2. **Project Settings** (`Metadata/project_settings.config`)
   - `filament_colour = #FF0000;#00FF00;...`

3. **Mesh XML** (`3D/Objects/*.model`) ← Most reliable!
   - `paint_color="0"` on triangle elements
   - Values like 0, 4, 8 indicate extruder slots

The mock parses ALL of these, just like the real backend.

## API Endpoints

### ML API (Port 8001)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/quotes/analyze-3mf` | Parse 3MF, detect materials, extract thumbnail |
| `POST /api/quotes/generate` | Generate quote (fake pricing, real file analysis) |
| `GET /api/quotes/profile-options` | Available materials/qualities |

### ERP API (Port 8000)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/materials/options` | Material list with colors |
| `POST /api/v1/auth/portal/login` | Mock login (always succeeds) |
| `POST /api/v1/auth/portal/register` | Mock registration |
| `POST /api/v1/quotes/portal` | Save quote to "database" |
| `POST /api/v1/quotes/portal/:id/accept` | Accept quote |
| `POST /api/v1/shipping/rates` | Mock shipping rates |
| `POST /api/v1/payments/create-checkout` | Mock Stripe redirect |

## Adding Mock Data

### Materials

Edit `sample-responses/materials-options.json` to add/modify available materials and colors.

### Other Responses

Add JSON files to `sample-responses/` and load them with:
```javascript
const data = loadSampleResponse('my-response.json');
```

## Troubleshooting

### "No multi-material data found"
- Check if your 3MF has paint data (open in BambuStudio, look for colored regions)
- Some 3MFs from other slicers don't include color metadata

### Port already in use
```bash
# Kill existing processes
npx kill-port 8000 8001
npm start
```

### CORS errors
Make sure you're accessing the frontend via `localhost:5173`, not `127.0.0.1`

## Files

```
mock-api/
├── server.js              # Main server with 3MF parsing
├── package.json           # Dependencies (express, jszip, multer)
├── sample-responses/      # Static JSON responses
│   └── materials-options.json
└── uploads/               # Temp storage (auto-created)
```

## Why This Exists

The real FilaOps backend includes proprietary components:
- ML models trained on thousands of prints
- Cost formulas tuned for profitability  
- BambuStudio CLI integration for accurate slicing

This mock lets contributors work on the UI without needing any of that. You get **real file parsing** (so the UI behaves correctly) with **fake numbers** (so we're not giving away the pricing engine).

---

Questions? Check the main [CONTRIBUTING.md](../CONTRIBUTING.md) or open an issue!
