# REDDIT POST - r/3Dprinting

## Title Options (pick one):
1. "I got tired of paying $150/month for ERP software that doesn't understand filament, so I built my own"
2. "Built an open-source ERP for my print farm - handles multi-color quoting, BOMs, and production tracking"
3. "After 8 months of spreadsheet hell, I built a proper production system for my print farm (now open source)"

---

## Post Body:

Hey everyone,

I run a small print farm (mix of Bambu P1S, A1s, and some Enders) and hit a wall last year trying to scale. Spreadsheets weren't cutting it, and every ERP I looked at either:

- Cost $150+/month and still didn't understand how 3D printing works
- Treated filament like injection molding material
- Had no concept of multi-color prints or AMS workflows
- Required me to manually calculate material costs for every quote

So I built what I needed. It's called **FilaOps** and I just open-sourced it.

**What it does:**

- **Instant multi-color quoting** - Customer uploads a 3MF, system detects 7 colors, calculates per-region gram usage, spits out a price. No manual math.
- **Filament-aware inventory** - Track by material type (PLA Basic, PLA Silk, PETG-CF, etc.), color, and spool. Automatic reorder alerts.
- **Real BOMs** - When a customer orders that 7-color traffic cone, the system knows exactly how much of each filament it needs plus packaging.
- **Production tracking** - Work centers, operation times, cost per step. I know my actual cost-to-produce, not a guess.
- **Traceability** - Lot tracking and serial numbers. I sell to some medical/aerospace customers who need this.

**Screenshots:**

[Customer Quote Portal - Upload 3MF, get instant multi-color pricing]

[BOM Detail - Full material and process cost breakdown]

[Dashboard - Production status at a glance]

**The tech:**
- Python/FastAPI backend
- SQL Server (yeah I know, but I come from regulated manufacturing)
- React frontend
- BSL 1.1 license (converts to Apache 2.0 in 4 years)

**What's NOT included (yet):**
The customer-facing quote portal and multi-color magic is going to be part of a paid "Pro" tier I'm working on. The open source version has the full ERP - products, BOMs, inventory, orders, production, traceability. You can absolutely run a print farm on it.

GitHub: https://github.com/Blb3D/filaops

I'm not trying to sell anything here - genuinely just want to see if this is useful to anyone else. If you run a print farm and have feedback, I'd love to hear what features matter to you.

Happy to answer questions about the build or the business side of running a print farm.

---

# REDDIT POST - r/BambuLab

## Title:
"Built an ERP that actually understands AMS/multi-color prints - open sourced it"

---

## Post Body:

Fellow Bambu owners,

Quick context: I run a print farm with P1S and A1 machines. The AMS is amazing for multi-color work but quoting those jobs was killing me. "How much filament per color? What's my actual cost? Did I account for the purge tower?"

I built a system that handles this automatically and just open-sourced the core ERP.

**The multi-color workflow:**

1. Customer uploads a 3MF (exported from BambuStudio)
2. System parses the file, detects all color regions
3. Calculates gram usage per color (including purge estimates)
4. Shows customer both single-color and multi-color pricing
5. They pick colors from my available inventory
6. Order flows into production with a proper BOM

No more "let me slice this and get back to you in an hour."

**Screenshot of the quote portal:**
[traffic cone example - 7 colors detected, per-region breakdown, instant pricing]

The open source version has the full ERP (inventory, BOMs, orders, production tracking). The quote portal shown above will be part of a Pro tier I'm building.

GitHub: https://github.com/Blb3D/filaops

Anyone else running a print business on Bambu hardware? Curious how you're handling quoting and production tracking.

---

# REDDIT POST - r/selfhosted

## Title:
"Open source ERP for 3D print farms - self-hosted, Python/FastAPI, SQL Server"

---

## Post Body:

Just released an ERP system I've been building for my 3D printing business. Figured the selfhosted crowd might appreciate it.

**FilaOps** - production-grade manufacturing resource planning for additive manufacturing.

**Stack:**
- Python 3.11+ / FastAPI
- SQLAlchemy ORM
- SQL Server Express (free tier works fine)
- React frontend
- Docker-ready (compose file included)

**What it handles:**
- Product catalog with variants
- Multi-level Bill of Materials
- Inventory management with reorder points
- Sales orders from multiple channels
- Production orders with operation tracking
- Work centers and routing
- Serial/lot traceability (FDA/ISO ready)

**Why SQL Server?**
I come from regulated manufacturing (medical devices) where SQL Server is standard. The codebase could be adapted for Postgres without too much pain if someone wants to PR it.

**License:** BSL 1.1 → Apache 2.0 after 4 years

GitHub: https://github.com/Blb3D/filaops

It's tailored for 3D printing workflows but the core ERP patterns would work for other small manufacturing operations. Happy to answer questions about the architecture.
