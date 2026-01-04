# Frequently Asked Questions (FAQ)

Common questions about FilaOps from print farm owners and users.

---

## Installation & Setup

### How do I install FilaOps?

FilaOps offers two installation methods:

**Option 1: Docker (Recommended for quick start)**
```bash
git clone https://github.com/Blb3D/filaops.git
cd filaops
cp .env.example .env
docker-compose up --build
```
Only requires Docker Desktop. See **[Docker Setup Guide](FilaOps_Zero-to-Running_Docker.md)**.

**Option 2: Native Installation**
- **[Windows Setup Guide](FilaOps_Zero-to-Running_Windows.md)**
- **[macOS/Linux Setup Guide](FilaOps_Zero-to-Running_macOS_Linux_SSH.md)**

Native installation requires Python 3.11+, Node.js 18+, and PostgreSQL 16+.

---

### Do I need to install Python, Node.js, or PostgreSQL?

**If using Docker:** No! Docker handles everything.

**If using native installation:** Yes. You'll need:
- Python 3.11+
- Node.js 18+
- PostgreSQL 16+

---

### What are the system requirements?

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 4GB | 8GB+ |
| Storage | 10GB | 20GB+ |
| CPU | 2 cores | 4+ cores |
| OS | Win 10, macOS 11, Ubuntu 20.04 | Latest versions |

---

### Can I run FilaOps on a Raspberry Pi?

Not recommended. FilaOps requires PostgreSQL, which needs more resources than a Raspberry Pi typically provides. Consider a small desktop computer or cloud server instead.

---

## Features & Capabilities

### Can I use FilaOps for my print farm?

Yes! FilaOps is specifically designed for 3D print farms. It handles:
- Multi-material prints
- Inventory tracking (filament by grams)
- Production orders and scheduling
- Material Requirements Planning (MRP)
- Customer orders and shipping

---

### Does FilaOps connect to my printers?

**Open Source version:** No. You manually enter production data.

**FilaOps Pro/Enterprise:** Yes. Includes:
- Bambu printer fleet management
- Automatic job dispatch
- Live print monitoring
- ML-based time estimation

---

### Can I track filament by the spool?

Yes! You can create lots/batches for each spool:
- Lot: `PLA-BLK-2025-0042`
- Quantity: 1000g
- Vendor lot: (from spool label)

When you load a spool, consume from that lot. This is especially useful for:
- Quality control (tracking which spool had issues)
- Expiration dates
- Vendor lot recalls

**Note:** Basic lot tracking is available in Open Source. Advanced traceability (FIFO/LIFO/FEFO) is in Pro/Enterprise.

---

### How do I handle multi-material prints?

Create a BOM with multiple filament lines:

```
Benchy (Multi-Color) BOM:
  PLA White: 30g (hull)
  PLA Red: 5g (flag)
  PLA Black: 2g (details)
```

FilaOps will track consumption for each material separately.

---

### How do I handle reprints/failures?

When completing a production operation:
1. Enter **Qty Good** and **Qty Bad**
2. Bad quantity is automatically scrapped (inventory adjusted)
3. If you need more, create a new production order for the shortage

---

### Can multiple people use FilaOps at the same time?

Yes! It's a web application. Multiple users can:
- Access the admin dashboard simultaneously
- Create orders, update inventory, start production
- View the same data in real-time

**Note:** User roles and permissions are coming in a future release.

---

### Does FilaOps calculate costs automatically?

Yes! FilaOps calculates:
- Material costs (based on filament consumption)
- Manufacturing costs (based on machine time)
- Total cost per unit
- Profit margins

You can see cost breakdowns in:
- Production orders
- Sales orders
- Dashboard analytics (Pro tier)

---

## Data Import & Export

### Can I import my existing products/customers/orders?

Yes! FilaOps supports CSV import for:
- **Products** - From Squarespace, Shopify, WooCommerce, Etsy, TikTok Shop, or generic CSV
- **Customers** - From any marketplace export
- **Orders** - From Squarespace, Shopify, WooCommerce, Etsy, TikTok Shop
- **Materials** - Filament inventory with template download

**See:** 
- [docs/MARKETPLACE_IMPORT_GUIDE.md](docs/MARKETPLACE_IMPORT_GUIDE.md) - Complete import guide
- [docs/SQUARESPACE_IMPORT_GUIDE.md](docs/SQUARESPACE_IMPORT_GUIDE.md) - Squarespace-specific guide

---

### What if my CSV doesn't match the expected format?

FilaOps automatically recognizes column names from major marketplaces:
- **SKU columns:** `SKU`, `Product SKU`, `Item SKU`, `Variant SKU`
- **Name columns:** `Title`, `Product Name`, `Name`, `Item Name`
- **Price columns:** `Price`, `Selling Price`, `Regular Price`, `Amount`

If your CSV uses different column names, you can:
1. Rename columns to match FilaOps expectations
2. Use the generic CSV format (see import guide)
3. Report the issue on GitHub - we can add support for your marketplace

---

### Can I export my data?

Yes! You can export:
- Products (CSV)
- Sales orders (CSV)
- Inventory reports (coming soon)

**Note:** Full export/import functionality is available in Pro tier.

---

## Inventory & Materials

### How does FilaOps handle different spool sizes?

FilaOps tracks inventory in **grams** (the stock unit), but you can purchase in different spool sizes (250g, 500g, 750g, 1kg, 3kg, 5kg).

**Dual UOM (Unit of Measure)** feature:
- **Purchase UOM:** Spools (1kg, 3kg, etc.)
- **Stock UOM:** Grams
- Automatic conversion when receiving inventory

This is a **Core/Open Source** feature.

---

### What if I run out of a material?

FilaOps will:
1. Show **low stock alerts** on the dashboard
2. Calculate **MRP shortages** (what you need for pending orders)
3. Help you create purchase orders (Pro tier)

You can set reorder points for each material.

---

### Can I track material by color and type?

Yes! FilaOps supports:
- Material types (PLA, PETG, ABS, TPU, etc.)
- Colors (Red, Blue, Black, etc.)
- Material-color combinations (PLA Red, PETG Blue, etc.)

Each combination gets its own SKU (e.g., `MAT-PLA-PLA_Basic-Red`).

---

## Orders & Production

### How does the order-to-production workflow work?

1. **Create Sales Order** - Customer places order
2. **Run MRP** - FilaOps calculates material requirements
3. **Check Inventory** - See if you have enough materials
4. **Create Production Order** - Start manufacturing
5. **Complete Production** - Enter quantities (good/bad)
6. **Create Shipment** - Package and ship to customer

**See:** [HOW_IT_WORKS.md](HOW_IT_WORKS.md) for detailed workflow.

---

### What if I don't have enough materials for an order?

FilaOps will:
1. Show **material shortages** in the order detail page
2. Calculate exactly how much you need
3. Help you create purchase orders (Pro tier)

You can still start production, but you'll see warnings about insufficient materials.

---

### Can I schedule production orders?

Yes! The Production page shows:
- All pending production orders
- Material availability
- Production status (Not Started, In Progress, Complete)

**Note:** Advanced scheduling and capacity planning is in Pro/Enterprise tiers.

---

## Pricing & Tiers

### What's the difference between Open Source, Pro, and Enterprise?

| Feature | Open Source | Pro | Enterprise |
|---------|:----------:|:---:|:----------:|
| Products, BOMs, Inventory | ✅ | ✅ | ✅ |
| Orders & Production | ✅ | ✅ | ✅ |
| MRP Planning | ✅ | ✅ | ✅ |
| CSV Import/Export | ✅ | ✅ | ✅ |
| Analytics Dashboard | ❌ | ✅ | ✅ |
| Printer Integration | ❌ | ✅ | ✅ |
| Advanced Traceability | ❌ | ❌ | ✅ |
| API Access | ❌ | ✅ | ✅ |
| Priority Support | ❌ | ✅ | ✅ |

**See:** [README.md](README.md) for full feature comparison.

---

### Is FilaOps really free?

**Open Source version:** Yes! Free forever for:
- Personal use
- Internal business use
- Educational use

**Restrictions:**
- Cannot be used to offer competing SaaS
- Converts to Apache 2.0 license after 4 years

**See:** [LICENSE](LICENSE) for full details.

---

### When will Pro/Enterprise be available?

Pro tier is in development. Sign up for updates:

- [GitHub Discussions](https://github.com/Blb3D/filaops/discussions)

---

## Technical Questions

### What database does FilaOps use?

FilaOps uses **PostgreSQL 16+** for all installations (Windows, macOS, and Linux).

---

### Can I use a different database?

Not currently. FilaOps is designed for PostgreSQL. Support for other databases may be added in the future.

---

### Can I run FilaOps on a server/cloud?

Yes! FilaOps can run on:
- Local computer
- Home server
- Cloud server (AWS, DigitalOcean, etc.)
- VPS

**Docker is recommended for servers** - it simplifies deployment and updates.

**Note:** For production use, consider:
- Setting up SSL/HTTPS (use a reverse proxy like nginx or Traefik)
- Regular database backups
- Firewall configuration
- Docker resource limits

---

### How do I backup my data?

**If using Docker:**
```bash
# Backup
docker-compose exec db pg_dump -U postgres filaops > filaops_backup.sql

# Restore
docker-compose exec -T db psql -U postgres filaops < filaops_backup.sql
```

**If using native installation:**
```bash
# Backup database
pg_dump -U postgres -d filaops -F c -f filaops_backup.dump

# Restore database
pg_restore -U postgres -d filaops -c filaops_backup.dump
```

Or use pgAdmin or other PostgreSQL management tools for GUI-based backups.

**Note:** Automated backup solutions coming in Pro tier.

---

### Can I customize FilaOps?

**Open Source:** Yes! You can:
- Modify the code
- Add features
- Customize the UI

**Contributions welcome!** See [CONTRIBUTING.md](CONTRIBUTING.md).

**Pro/Enterprise:** Customization services available. Contact for details.

---

## Troubleshooting

### I'm getting "Cannot connect to server" errors

1. Check if backend is running (port 8000)
2. Check if frontend is running (port 5173)
3. Verify PostgreSQL is running and accessible
4. Check your `.env` file has correct database credentials
5. Verify database exists: `psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='filaops';"`

**See:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed help.

---

### My CSV import failed with errors

Common issues:
1. **Wrong column names** - FilaOps auto-detects, but check the import guide
2. **Missing required fields** - SKU, Name, or Price might be missing
3. **Invalid data** - Check for special characters or formatting issues

**See:** [docs/MARKETPLACE_IMPORT_GUIDE.md](docs/MARKETPLACE_IMPORT_GUIDE.md) for solutions.

---

### The dashboard shows "Failed to fetch"

This usually means:
1. Backend server isn't running (check port 8000)
2. Database connection failed (verify PostgreSQL is running)
3. Port conflict (something else using port 8000 or 5173)
4. CORS configuration issue (check backend CORS settings)

**See:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions.

---

## Getting Help

### Where can I get help?

1. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Detailed troubleshooting guide
2. **[GitHub Issues](https://github.com/Blb3D/filaops/issues)** - Report bugs
3. **[GitHub Discussions](https://github.com/Blb3D/filaops/discussions)** - Ask questions

---

### How do I report a bug?

1. Check if it's already reported: [GitHub Issues](https://github.com/Blb3D/filaops/issues)
2. If not, create a new issue with:
   - What you were trying to do
   - What happened (error message, screenshots)
   - Steps to reproduce
   - Your setup (OS, PostgreSQL version, Python version, etc.)

---

### Can I request a feature?

Yes! Use [GitHub Discussions](https://github.com/Blb3D/filaops/discussions) to:
- Request new features
- Vote on existing requests
- Discuss ideas with the community

---

## Still Have Questions?

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Detailed troubleshooting
- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - How FilaOps works
- **[GitHub Discussions](https://github.com/Blb3D/filaops/discussions)** - Community Q&A

---

*Last updated: December 2025*

