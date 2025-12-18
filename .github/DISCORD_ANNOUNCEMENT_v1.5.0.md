# Discord Announcement - v1.5.0

---

## Short Version (Announcements Channel)

```
🚀 **FilaOps v1.5.0 is Live!**

New features:
✅ Activity Timeline on order pages
✅ Work Centers & Machines management
✅ Fixed purchasing page crash
✅ SQL Server compatibility improvements

**Upgrade now**: https://github.com/Blb3D/filaops/blob/main/UPGRADE.md

⚠️ **Important**: This release has 3 database migrations. Run `alembic upgrade head` after pulling!

Questions? Head to #support or GitHub Discussions:
https://github.com/Blb3D/filaops/discussions
```

---

## Long Version (General/Updates Channel)

```
🎉 **v1.5.0 Release - Repository Cleanup and UI Improvements**

Hey @everyone! We just released v1.5.0 with some great improvements.

**🆕 What's New:**

**Activity Timeline** - Beautiful visual timeline showing order events (created, confirmed, shipped, completed)

**Work Centers & Machines** - Manage your production resources (3D printer pools, assembly stations, etc.) - foundation for production scheduling!

**Bug Fixes** 🐛
- Fixed the purchasing page crash (low-stock calculation TypeError)
- Payment validation now prevents future dates and 6-digit years
- Production deployments now fail safely if using default SECRET_KEY

**Code Quality** 🔧
- SQL Server compatibility across 66 files
- Type hints for better IDE support
- Security improvements (JWT tokens removed from git)
- Better error messages

**📦 How to Upgrade:**

```bash
git fetch --tags
git checkout v1.5.0
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d

# IMPORTANT - Run migrations!
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Clear browser cache (Ctrl + Shift + R)
```

**⏱️ Upgrade time**: ~5 minutes
**⚠️ Database migrations**: 3 new migrations (additive only - safe)

**Full upgrade guide**: https://github.com/Blb3D/filaops/blob/main/UPGRADE.md
**Release notes**: https://github.com/Blb3D/filaops/releases/tag/v1.5.0

**Questions?** Drop them in #support or on GitHub Discussions!

**What's Next:** v1.6.0 (Q1 2026) - Production builds, performance improvements, enhanced error handling

Happy upgrading! 🚀
```

---

## Support Channel Response Template

When users ask about upgrading:

```
Hey! The upgrade process is pretty straightforward:

1. **Pull the release**: `git checkout v1.5.0`
2. **Rebuild containers**: `docker-compose -f docker-compose.dev.yml build --no-cache`
3. **Restart**: `docker-compose -f docker-compose.dev.yml up -d`
4. **Run migrations**: `docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head`
5. **Clear browser cache**: Ctrl + Shift + R

Full guide: https://github.com/Blb3D/filaops/blob/main/UPGRADE.md

The 3 database migrations are for work centers, machines, and fulfillment tracking. They're additive only - your data is safe!

Let me know if you run into any issues! 👍
```

---

## Common Support Responses

### "Containers won't start"
```
Check if something's using port 5174:
Windows: `netstat -ano | findstr :5174`
Linux/Mac: `lsof -i :5174`

Or try removing volumes and restarting:
`docker-compose -f docker-compose.dev.yml down -v`
`docker-compose -f docker-compose.dev.yml up -d`
```

### "Getting JavaScript errors"
```
Clear your browser cache! The frontend was updated.
- Hard refresh: Ctrl + Shift + R (Windows/Linux) or Cmd + Shift + R (Mac)
- Or use incognito mode
```

### "Migration failed"
```
Check the migration status:
`docker-compose -f docker-compose.dev.yml exec backend alembic current`

Can you share the error message? That'll help us troubleshoot!
```

### "Do I need to backup?"
```
The migrations are additive only (no data loss), but it's always smart to backup before upgrading. Quick backup:

**Using Docker volumes**: `docker-compose -f docker-compose.dev.yml exec db ... backup command`
**Using SQL Server Management Studio**: Right-click database → Tasks → Backup

You should be fine without it, but better safe than sorry!
```
