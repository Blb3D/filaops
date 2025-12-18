# 🚀 v1.5.0 is Live! How to Upgrade

Hey everyone! v1.5.0 is officially released and ready for you to upgrade. This release brings some great improvements and fixes.

## TL;DR - Quick Upgrade

```bash
# 1. Get the latest code
cd filaops
git fetch --tags
git checkout v1.5.0

# 2. Rebuild containers
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d

# 3. Run database migrations (IMPORTANT!)
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# 4. Clear browser cache (Ctrl+Shift+R)
```

That's it! 🎉

---

## What's New?

### 🆕 New Features

**Activity Timeline** - You can now see a visual timeline of order events right on the order detail page. Track when orders were created, confirmed, shipped, and completed.

**Work Centers & Machines** - Manage your production resources like 3D printer pools and assembly stations. This lays the foundation for production scheduling.

**Better Testing** - Comprehensive E2E test suite to catch bugs before they affect you.

### 🐛 Bug Fixes

We fixed some important bugs:
- **Purchasing page crash** - Fixed the TypeError that was crashing the low-stock calculation
- **Payment validation** - No more 6-digit years! Payments are now validated properly
- **Security** - Production deployments now fail if you're using the default SECRET_KEY

### 🔧 Under the Hood

- SQL Server compatibility improvements (66 files updated)
- Better error messages throughout
- Type hints for better IDE support
- Removed JWT tokens from git tracking (security improvement)

**Full details**: https://github.com/Blb3D/filaops/releases/tag/v1.5.0

---

## ⚠️ Important: Database Migrations

v1.5.0 adds **3 new database migrations** for work centers, machines, and fulfillment tracking.

**You MUST run this after upgrading:**

```bash
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head
```

Don't worry - these migrations are **additive only**. Your existing data is safe.

---

## Need Help?

### Common Issues

**"Cannot access before initialization" errors**
- Your browser cached old JavaScript
- Fix: Hard refresh (`Ctrl + Shift + R`) or use incognito mode

**Containers won't start**
- Usually a port conflict
- Check what's using port 5174: `netstat -ano | findstr :5174` (Windows)
- Or try: `docker-compose -f docker-compose.dev.yml down -v` and restart

**Migration fails**
- Check migration status: `docker-compose -f docker-compose.dev.yml exec backend alembic current`
- If stuck, post the error here and we'll help!

### Full Upgrade Guide

For detailed instructions (including non-Docker installations):
👉 **[UPGRADE.md](https://github.com/Blb3D/filaops/blob/main/UPGRADE.md)**

---

## Questions?

Drop your questions below! Common ones:

**Q: Do I need to backup my database?**
A: Always a good idea, but migrations are safe (additive only).

**Q: Will this break my existing orders?**
A: Nope! All changes are backward compatible.

**Q: How long does the upgrade take?**
A: Usually < 5 minutes total.

**Q: Can I skip the migrations?**
A: **No!** The app won't work properly without them.

---

## Upgraded Successfully?

If you've upgraded successfully, let us know! A quick "✅ Upgraded on Windows/Linux/Mac" helps others feel confident.

Found a bug? **Report it here**: https://github.com/Blb3D/filaops/issues

---

## What's Next?

**v1.6.0** (Planned Q1 2026):
- Production build optimizations
- Enhanced error handling
- Performance improvements
- More manufacturing features

Subscribe to releases to get notified: https://github.com/Blb3D/filaops/releases

---

Happy upgrading! 🎉

*Questions, issues, or feedback? Reply below!*
