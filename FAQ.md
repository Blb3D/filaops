# Frequently Asked Questions (FAQ)

Common questions about FilaOps from print farm owners and users.

---

## Installation & Setup

### Should I use Docker or manual installation?

**Use Docker** (recommended) if:
- You want the fastest setup (10-15 minutes)
- You're not comfortable with Python/Node.js/SQL Server setup
- You want everything pre-configured
- You're running on Windows, macOS, or Linux

**Use manual installation** if:
- Docker isn't available on your system
- You need to customize the database configuration
- You're a developer who wants to modify the code

**See:** [GETTING_STARTED.md](GETTING_STARTED.md) for both methods.

---

### Do I need to install Python, Node.js, or SQL Server?

**With Docker:** No! Everything runs in containers. You only need Docker Desktop.

**With manual installation:** Yes. You'll need:
- Python 3.11+
- Node.js 18+
- SQL Server Express (Windows) or PostgreSQL (Linux/Mac)

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

Not recommended. FilaOps requires SQL Server (or PostgreSQL), which needs more resources than a Raspberry Pi typically provides. Consider a small desktop computer or cloud server instead.

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

**Docker version:** SQL Server (included in container)

**Manual installation:** 
- Windows: SQL Server Express
- Linux/Mac: PostgreSQL (with manual setup)

---

### Can I use a different database?

Not currently. FilaOps is designed for SQL Server/PostgreSQL. Support for other databases may be added in the future.

---

### Can I run FilaOps on a server/cloud?

Yes! FilaOps can run on:
- Local computer
- Home server
- Cloud server (AWS, DigitalOcean, etc.)
- VPS

**Note:** For production use, consider:
- Setting up SSL/HTTPS
- Regular database backups
- Firewall configuration

---

### How do I backup my data?

**Docker:**
```bash
# Backup database
docker exec filaops-db /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourPassword -Q "BACKUP DATABASE FilaOps TO DISK='/var/opt/mssql/backup/FilaOps.bak'"
```

**Manual:** Use SQL Server Management Studio or PostgreSQL backup tools.

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

**Docker:**
1. Check if containers are running: `docker-compose ps`
2. Check logs: `docker-compose logs backend`
3. Make sure Docker Desktop is running

**Manual:**
1. Check if backend is running (port 8000)
2. Check if frontend is running (port 5173)
3. Verify database connection

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
1. Backend server isn't running
2. Database connection failed
3. Port conflict (something else using port 8000)

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
   - Your setup (Docker or manual, OS, etc.)

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

