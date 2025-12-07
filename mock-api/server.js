/**
 * FilaOps Quote Portal - Mock API Server
 * 
 * This server provides API responses for frontend development.
 * It ACTUALLY PARSES 3MF files to extract real color/material data,
 * but returns fake pricing (since the real quoter is proprietary).
 * 
 * Contributors can run this instead of the full backend stack.
 * 
 * Usage:
 *   cd mock-api
 *   npm install
 *   npm start
 * 
 * Then run the frontend with:
 *   npm run dev
 */

import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import JSZip from 'jszip';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();

// Configure multer to preserve original filename
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = join(__dirname, 'uploads');
    if (!existsSync(uploadDir)) {
      mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    // Use timestamp + original name to avoid collisions
    const uniqueName = `${Date.now()}-${file.originalname}`;
    cb(null, uniqueName);
  }
});
const upload = multer({ storage });

// Enable CORS for frontend dev server
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:5174', 'http://localhost:3000'],
  credentials: true
}));

app.use(express.json());

// Serve static files from uploads
app.use('/uploads', express.static(join(__dirname, 'uploads')));

// Helper to load sample responses
function loadSampleResponse(filename) {
  const path = join(__dirname, 'sample-responses', filename);
  if (existsSync(path)) {
    return JSON.parse(readFileSync(path, 'utf8'));
  }
  return null;
}

// ============================================================================
// 3MF PARSER - Extract real material/color data from uploaded files
// ============================================================================

/**
 * Parse paint_color attribute from BambuStudio 3MF mesh triangles.
 * Returns the extruder index (0-based).
 * 
 * BambuStudio uses values like "0", "4", "8" for different slots.
 */
function parseBambuPaintColor(value) {
  if (!value) return null;
  const num = parseInt(value, 10);
  return isNaN(num) ? null : num;
}

/**
 * Parse a 3MF file to extract material slots, colors, and thumbnail.
 * This mirrors the logic in the real backend's threemf_analyzer.py
 * AND the frontend's ModelViewer.jsx MMU parser.
 */
async function parse3MF(filePath) {
  const result = {
    success: true,
    is_multi_material: false,
    material_count: 1,
    material_slots: [],
    original_colors: [],
    thumbnail_url: null,
    model_name: filePath.split(/[/\\]/).pop().replace('.3mf', '')
  };

  try {
    const data = readFileSync(filePath);
    const zip = await JSZip.loadAsync(data);
    
    console.log('[3MF Parser] Parsing:', result.model_name);
    
    // Extract thumbnail if available
    const thumbnailPaths = [
      'Metadata/plate_1.png',
      'Metadata/thumbnail.png',
      'thumbnail.png',
      'Thumbnails/thumbnail.png'
    ];
    
    for (const thumbPath of thumbnailPaths) {
      const thumbFile = zip.file(thumbPath);
      if (thumbFile) {
        try {
          const thumbData = await thumbFile.async('nodebuffer');
          const thumbFilename = `thumb_${Date.now()}.png`;
          const thumbFullPath = join(__dirname, 'uploads', thumbFilename);
          writeFileSync(thumbFullPath, thumbData);
          result.thumbnail_url = `/uploads/${thumbFilename}`;
          console.log('[3MF Parser] Extracted thumbnail:', thumbPath);
          break;
        } catch (e) {
          console.log('[3MF Parser] Failed to extract thumbnail:', e.message);
        }
      }
    }

    // Track extruders and colors from multiple sources
    const filamentColors = {};
    const usedExtruders = new Set();

    // =========================================================================
    // METHOD 1: Parse plate JSON files (BambuStudio metadata format)
    // =========================================================================
    for (const filename of Object.keys(zip.files)) {
      if (filename.includes('plate_') && filename.endsWith('.json')) {
        try {
          const content = await zip.file(filename).async('string');
          const plateData = JSON.parse(content);
          console.log('[3MF Parser] Found plate config:', filename);

          // Extract filament IDs and colors
          if (plateData.filament_ids) {
            plateData.filament_ids.forEach((id, idx) => {
              if (id) {
                usedExtruders.add(idx);
                const colors = plateData.filament_colours || [];
                if (colors[idx] && colors[idx] !== '#00000000') {
                  filamentColors[idx] = colors[idx];
                }
              }
            });
          }

          // Check AMS mapping
          if (plateData.ams_mapping && Array.isArray(plateData.ams_mapping)) {
            plateData.ams_mapping.forEach((slot, idx) => {
              if (slot !== null && slot !== -1) {
                usedExtruders.add(idx);
              }
            });
          }

          // Direct filament colours
          if (plateData.filament_colours) {
            plateData.filament_colours.forEach((color, idx) => {
              if (color && color !== '#00000000' && color !== '') {
                filamentColors[idx] = color;
              }
            });
          }
        } catch (e) {
          console.log('[3MF Parser] Error parsing', filename, e.message);
        }
      }

      // Also check project_settings.config for colors
      if (filename === 'Metadata/project_settings.config') {
        try {
          const content = await zip.file(filename).async('string');
          const colorMatch = content.match(/filament_colour\s*=\s*([^\n]+)/);
          if (colorMatch) {
            const colors = colorMatch[1].split(';').filter(c => c.trim());
            colors.forEach((color, idx) => {
              if (color && color !== '#00000000' && !filamentColors[idx]) {
                filamentColors[idx] = color.trim();
              }
            });
          }
        } catch (e) {
          console.log('[3MF Parser] Error parsing project_settings.config:', e.message);
        }
      }
    }

    // =========================================================================
    // METHOD 2: Parse mesh XML for paint_color attributes (BambuStudio painted models)
    // This is the CRITICAL method for detecting multi-color when plate JSON fails
    // =========================================================================
    const meshExtruders = new Set();
    
    for (const filename of Object.keys(zip.files)) {
      if (filename.endsWith('.model')) {
        try {
          const content = await zip.file(filename).async('string');
          
          // Quick regex scan for paint_color attributes (faster than full XML parse)
          const paintColorMatches = content.matchAll(/paint_color\s*=\s*"([^"]+)"/g);
          
          for (const match of paintColorMatches) {
            const value = match[1];
            // paint_color can be multi-digit for gradients, use first char as primary
            const extruder = parseBambuPaintColor(value.charAt(0));
            if (extruder !== null) {
              meshExtruders.add(extruder);
            }
          }
        } catch (e) {
          // Ignore parsing errors for individual model files
        }
      }
    }

    if (meshExtruders.size > 0) {
      console.log('[3MF Parser] Found paint_color extruders in mesh:', [...meshExtruders].sort((a,b) => a-b));
      // Add mesh extruders to our set
      for (const ext of meshExtruders) {
        usedExtruders.add(ext);
      }
    }

    // =========================================================================
    // BUILD MATERIAL SLOTS
    // =========================================================================
    const allIndices = new Set([...usedExtruders, ...Object.keys(filamentColors).map(Number)]);
    
    // Default colors for slots without explicit colors
    const defaultColors = [
      '#FF6B00', '#FFFFFF', '#000000', '#FFD700',  // Orange, White, Black, Gold
      '#00FF00', '#0000FF', '#FF00FF', '#00FFFF',  // Green, Blue, Magenta, Cyan
      '#FF0000', '#800080', '#FFA500', '#008080'   // Red, Purple, Orange, Teal
    ];

    if (allIndices.size > 1) {
      // Multi-material detected!
      const sortedIndices = [...allIndices].sort((a, b) => a - b);
      
      for (const idx of sortedIndices) {
        const color = filamentColors[idx] || defaultColors[idx % defaultColors.length];
        result.material_slots.push({
          slot_index: idx,
          name: `Filament ${idx + 1}`,
          display_color: color
        });
        result.original_colors.push(color);
      }

      result.is_multi_material = true;
      result.material_count = result.material_slots.length;
      
      console.log('[3MF Parser] Multi-material detected:', result.material_count, 'materials');
      console.log('[3MF Parser] Colors:', result.original_colors);
    } else if (allIndices.size === 1) {
      // Single material with explicit index
      const idx = [...allIndices][0];
      const color = filamentColors[idx] || defaultColors[0];
      result.material_slots = [{ slot_index: idx, name: 'Filament 1', display_color: color }];
      result.original_colors = [color];
      console.log('[3MF Parser] Single material detected');
    } else {
      // No material info found - default
      result.material_slots = [{ slot_index: 0, name: 'Default', display_color: '#808080' }];
      result.original_colors = ['#808080'];
      console.log('[3MF Parser] No material data found, using defaults');
    }

  } catch (e) {
    console.error('[3MF Parser] Error:', e.message);
    result.success = false;
    result.error = e.message;
  }

  return result;
}

/**
 * Generate fake but realistic quote data based on parsed 3MF
 */
function generateMockQuote(analysis, material = 'PLA', quality = 'standard', infill = 20) {
  const materialCount = analysis.material_count || 1;
  
  // Generate realistic-ish weights per material (random but proportional)
  const totalWeight = 50 + Math.random() * 200; // 50-250g total
  const weights = [];
  let remaining = totalWeight;
  
  for (let i = 0; i < materialCount; i++) {
    if (i === materialCount - 1) {
      weights.push(Math.round(remaining * 10) / 10);
    } else {
      const portion = remaining * (0.3 + Math.random() * 0.4);
      weights.push(Math.round(portion * 10) / 10);
      remaining -= portion;
    }
  }
  
  // Sort weights descending (primary color usually has most material)
  weights.sort((a, b) => b - a);

  // Calculate fake price based on weight
  const pricePerGram = 0.05 + Math.random() * 0.03; // $0.05-0.08/g
  const multiMaterialMultiplier = materialCount > 1 ? 1.5 : 1.0;
  const totalPrice = Math.round(totalWeight * pricePerGram * multiMaterialMultiplier * 100) / 100;
  const singleColorPrice = Math.round(totalWeight * pricePerGram * 100) / 100;

  // Calculate fake print time (roughly 1 hour per 20g)
  const printTimeMinutes = Math.round(totalWeight * 3 + (materialCount - 1) * 30);

  return {
    success: true,
    filename: analysis.model_name + '.3mf',
    model_url: null, // Will be set by caller

    is_multi_material: analysis.is_multi_material,
    multi_material: analysis.is_multi_material ? {
      is_multi_material: true,
      material_count: materialCount,
      filament_types: Array(materialCount).fill(material),
      filament_weights_grams: weights,
      filament_colours: analysis.original_colors,
      tool_change_count: Math.round(weights.reduce((a, b) => a + b, 0) * 0.5)
    } : null,

    dimensions: {
      x: 50 + Math.random() * 100,
      y: 50 + Math.random() * 100,
      z: 20 + Math.random() * 80
    },

    material_grams: Math.round(totalWeight * 10) / 10,
    print_time_hours: Math.round(printTimeMinutes / 60 * 100) / 100,

    unit_price: totalPrice,
    total_price: totalPrice,

    single_color_alternative: {
      price: singleColorPrice,
      time_minutes: Math.round(printTimeMinutes * 0.7),
      time_saved_minutes: Math.round(printTimeMinutes * 0.3),
      material_saved_cost: Math.round((totalPrice - singleColorPrice) * 100) / 100,
      note: "Single color uses less material (no purge tower)"
    },

    base_quote: {
      time_minutes: printTimeMinutes,
      price: totalPrice,
      material_grams: totalWeight
    },

    ml_quote: {
      time_minutes: Math.round(printTimeMinutes * 1.03),
      price: Math.round(totalPrice * 1.03 * 100) / 100,
      correction_factor: 1.03
    },

    ml_status: "mock",

    production_profile: {
      printer_name: "MockPrinter",
      printer_model: "P1S",
      material: material,
      quality: quality,
      infill: quality,
      layer_height: quality === 'fine' ? 0.12 : quality === 'draft' ? 0.28 : 0.2,
      infill_percentage: infill
    }
  };
}

// ============================================================================
// ML API (Port 8001) - Slicer/Quote Generation
// ============================================================================

// Store analysis results for use in generate endpoint
const analysisCache = new Map();

// Analyze 3MF for multi-material
app.post('/api/quotes/analyze-3mf', upload.single('file'), async (req, res) => {
  console.log('[Mock] POST /api/quotes/analyze-3mf');
  console.log('  File:', req.file?.originalname || 'none');
  
  if (!req.file) {
    return res.status(400).json({ success: false, error: 'No file uploaded' });
  }

  try {
    const analysis = await parse3MF(req.file.path);
    
    // Cache for generate endpoint
    analysisCache.set(req.file.originalname, analysis);
    
    // Store file path for serving
    analysis.model_url = `/uploads/${req.file.filename}`;
    
    console.log('[Mock] Analysis result:', {
      is_multi_material: analysis.is_multi_material,
      material_count: analysis.material_count,
      colors: analysis.original_colors
    });

    res.json(analysis);
  } catch (e) {
    console.error('[Mock] Analysis error:', e);
    res.status(500).json({ success: false, error: e.message });
  }
});

// Generate quote (main slicer endpoint)
app.post('/api/quotes/generate', upload.single('file'), async (req, res) => {
  console.log('[Mock] POST /api/quotes/generate');
  console.log('  File:', req.file?.originalname || 'none');
  console.log('  Material:', req.body.material);
  console.log('  Quality:', req.body.quality);
  console.log('  Infill:', req.body.infill);
  
  if (!req.file) {
    return res.status(400).json({ success: false, error: 'No file uploaded' });
  }

  try {
    // Check cache first, otherwise parse
    let analysis = analysisCache.get(req.file.originalname);
    if (!analysis) {
      analysis = await parse3MF(req.file.path);
    }

    // Generate mock quote based on real analysis
    const quote = generateMockQuote(
      analysis,
      req.body.material || 'PLA',
      req.body.quality || 'standard',
      parseInt(req.body.infill) || 20
    );

    // Set model URL for 3D viewer
    quote.model_url = `/uploads/${req.file.filename}`;
    quote.filename = req.file.originalname;

    console.log('[Mock] Generated quote:', {
      is_multi_material: quote.is_multi_material,
      material_count: quote.multi_material?.material_count,
      weights: quote.multi_material?.filament_weights_grams,
      colors: quote.multi_material?.filament_colours,
      price: quote.total_price
    });

    // Simulate slicing delay (much shorter than real - just for UX)
    setTimeout(() => {
      res.json(quote);
    }, 1000);

  } catch (e) {
    console.error('[Mock] Quote generation error:', e);
    res.status(500).json({ success: false, error: e.message });
  }
});

// Profile options
app.get('/api/quotes/profile-options', (req, res) => {
  console.log('[Mock] GET /api/quotes/profile-options');
  res.json({
    success: true,
    options: {
      materials: ['PLA', 'PETG', 'ABS', 'TPU'],
      qualities: ['extra_draft', 'draft', 'standard', 'fine', 'extra_fine'],
      infills: ['light', 'standard', 'strong', 'solid']
    }
  });
});

// ============================================================================
// ERP API (Port 8000) - Materials, Quotes, Auth
// ============================================================================

// Get materials with colors
app.get('/api/v1/materials/options', (req, res) => {
  console.log('[Mock] GET /api/v1/materials/options');
  const response = loadSampleResponse('materials-options.json');
  res.json(response);
});

// Material pricing lookup
app.get('/api/v1/materials/pricing/:code', (req, res) => {
  console.log('[Mock] GET /api/v1/materials/pricing/' + req.params.code);
  res.json({
    base_price_per_kg: 24.99,
    price_multiplier: 1.0,
    density: 1.24,
    volumetric_flow_limit: null
  });
});

// Customer auth (mock - always succeeds)
app.post('/api/v1/auth/portal/login', (req, res) => {
  console.log('[Mock] POST /api/v1/auth/portal/login');
  res.json({
    id: 1,
    email: req.body.email,
    first_name: 'Test',
    last_name: 'User',
    customer_number: 'CUST-001'
  });
});

app.post('/api/v1/auth/portal/register', (req, res) => {
  console.log('[Mock] POST /api/v1/auth/portal/register');
  res.json({
    id: 1,
    email: req.body.email,
    first_name: req.body.first_name || 'New',
    last_name: req.body.last_name || 'User',
    customer_number: 'CUST-002'
  });
});

// Save quote to ERP
app.post('/api/v1/quotes/portal', (req, res) => {
  console.log('[Mock] POST /api/v1/quotes/portal');
  console.log('  Body:', JSON.stringify(req.body, null, 2).slice(0, 500));
  
  const quoteNumber = 'Q-' + Date.now().toString().slice(-8);
  res.json({
    id: Math.floor(Math.random() * 10000),
    quote_number: quoteNumber,
    status: 'pending',
    created_at: new Date().toISOString()
  });
});

// Accept quote
app.post('/api/v1/quotes/portal/:id/accept', (req, res) => {
  console.log('[Mock] POST /api/v1/quotes/portal/' + req.params.id + '/accept');
  res.json({
    success: true,
    quote_number: 'Q-' + req.params.id,
    requires_review: req.body.notes ? true : false
  });
});

// Shipping rates
app.post('/api/v1/shipping/rates', (req, res) => {
  console.log('[Mock] POST /api/v1/shipping/rates');
  res.json({
    success: true,
    rates: [
      { rate_id: 'rate_1', carrier: 'USPS', service: 'Priority Mail', display_name: 'USPS Priority (2-3 days)', rate: 8.95, est_delivery_days: 3 },
      { rate_id: 'rate_2', carrier: 'USPS', service: 'Ground Advantage', display_name: 'USPS Ground (5-7 days)', rate: 5.50, est_delivery_days: 6 },
      { rate_id: 'rate_3', carrier: 'UPS', service: 'Ground', display_name: 'UPS Ground (3-5 days)', rate: 12.99, est_delivery_days: 4 }
    ]
  });
});

// Create checkout session
app.post('/api/v1/payments/create-checkout', (req, res) => {
  console.log('[Mock] POST /api/v1/payments/create-checkout');
  res.json({
    checkout_url: 'http://localhost:5173/payment/success?session_id=mock_session&quote_id=' + req.body.quote_id
  });
});

// ============================================================================
// Server startup
// ============================================================================

const ML_PORT = 8001;
const ERP_PORT = 8000;

// Start on both ports to match real architecture
app.listen(ML_PORT, () => {
  console.log(`\n${'='.repeat(60)}`);
  console.log('🎭 MOCK API SERVER RUNNING (with real 3MF parsing!)');
  console.log('='.repeat(60));
  console.log(`\n📡 ML API (slicer):  http://localhost:${ML_PORT}`);
  console.log(`📡 ERP API (data):   http://localhost:${ERP_PORT}`);
  console.log(`\n💡 This mock PARSES real 3MF files to extract colors/materials`);
  console.log(`   - Reads plate JSON metadata`);
  console.log(`   - Scans mesh XML for paint_color attributes`);
  console.log(`   - Pricing is fake, but material detection is real!`);
  console.log(`\n🚀 Start the frontend with: npm run dev`);
  console.log('='.repeat(60) + '\n');
});

// Also listen on ERP port
app.listen(ERP_PORT, () => {
  // Silent - already logged above
});
