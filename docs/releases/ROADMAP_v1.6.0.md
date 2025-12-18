# v1.6.0 Roadmap - Version Awareness & Update Management

**Target Release**: Q1 2026
**Status**: Planning

---

## 🎯 Primary Goals

1. **Version Visibility** - Users should always know what version they're running
2. **Update Awareness** - Users should be notified when updates are available
3. **Easy Upgrades** - Streamline the upgrade process with clear guidance

---

## ✨ Planned Features

### 1. Version Display in UI

**Status**: Ready to implement
**Priority**: High

Display current version number in the application:
- Show in header/navbar next to FilaOps logo
- Format: "FilaOps v1.6.0" or "FilaOps ERP v1.6.0"
- Always visible to users

**Technical Details**:
- Read version from `package.json`
- Display in `AdminLayout.jsx` header (line 614)
- Responsive design (show/hide on mobile if needed)

**User Benefit**: Users can easily report their version when asking for support

---

### 2. Automatic Update Checker

**Status**: Ready to implement
**Priority**: High

Check for updates automatically and notify users:

**Behavior**:
- Check on app startup (once per session)
- Query GitHub API for latest release tag
- Compare with current version
- Show dismissible notification banner if update available

**Notification Content**:
- "New version available: v1.6.0 → v1.7.0"
- Link to release notes on GitHub
- Link to upgrade guide
- "Dismiss" and "Remind me later" options

**Technical Details**:
- GitHub API: `GET https://api.github.com/repos/Blb3D/filaops/releases/latest`
- No authentication required for public repos
- Cache result in sessionStorage (check once per session)
- Graceful failure if API unavailable

**User Benefit**: Stay informed about new features and bug fixes

---

### 3. Manual "Check for Updates" Button

**Status**: Ready to implement
**Priority**: Medium

Add manual check button in Admin Settings:

**Location**: Admin Settings page
**Behavior**:
- Button: "Check for Updates"
- On click: Query GitHub API
- Show modal with:
  - Current version
  - Latest version
  - "Up to date" or "Update available"
  - Link to changelog
  - Link to upgrade guide

**User Benefit**: Check for updates on demand without waiting for automatic check

---

### 4. Changelog Viewer (Optional)

**Status**: Future consideration
**Priority**: Low

Display changelog in-app:
- Fetch release notes from GitHub
- Render markdown
- Show what's new since user's version

**User Benefit**: See what's changed without leaving the app

---

## 🔧 Technical Implementation

### Frontend Changes

**New Files**:
```
frontend/src/hooks/useVersionCheck.js     - Hook for checking updates
frontend/src/components/UpdateNotification.jsx - Notification banner
frontend/src/utils/version.js             - Version utilities
```

**Modified Files**:
```
frontend/src/components/AdminLayout.jsx   - Add version display
frontend/src/pages/admin/AdminSettings.jsx - Add manual check button
frontend/package.json                     - Update version to 1.6.0
```

### Backend Changes

**Optional**: Add version endpoint for easier querying
```
GET /api/v1/version
Response: {"version": "1.6.0", "environment": "production"}
```

---

## 📊 Success Metrics

- Users can identify their version in < 5 seconds
- Update notifications have < 1% false positive rate
- 80%+ of users upgrade within 30 days of release

---

## 🚧 Implementation Phases

### Phase 1: Version Display (Week 1)
- [ ] Update `package.json` to v1.6.0-dev
- [ ] Add version display to header
- [ ] Test responsive design
- [ ] Commit and push

### Phase 2: Update Checker Hook (Week 1)
- [ ] Create `useVersionCheck` hook
- [ ] Implement GitHub API integration
- [ ] Add error handling and caching
- [ ] Write tests

### Phase 3: Update Notification (Week 2)
- [ ] Create `UpdateNotification` component
- [ ] Integrate with AdminLayout
- [ ] Add "Dismiss" and "Remind later" logic
- [ ] Test UX flow

### Phase 4: Manual Check Button (Week 2)
- [ ] Add button to AdminSettings
- [ ] Create check modal
- [ ] Link to documentation
- [ ] Test error cases

### Phase 5: Testing & Polish (Week 3)
- [ ] Test with different version scenarios
- [ ] Test API failure cases
- [ ] Test on production environment
- [ ] Get user feedback

### Phase 6: Release (Week 4)
- [ ] Update all documentation
- [ ] Create release notes
- [ ] Tag v1.6.0
- [ ] Announce to community

---

## 🧪 Testing Plan

### Manual Testing
- [ ] Fresh install shows correct version
- [ ] Update check works with internet connection
- [ ] Update check fails gracefully without internet
- [ ] Notification can be dismissed
- [ ] "Remind later" works correctly
- [ ] Manual check button works
- [ ] Links to docs are correct

### Automated Testing
- [ ] Unit tests for version comparison logic
- [ ] Mock GitHub API responses
- [ ] Test localStorage/sessionStorage handling

---

## 📚 Documentation Updates Needed

- [ ] Update UPGRADE.md with "Check for Updates" feature
- [ ] Add screenshot of version display
- [ ] Document GitHub API rate limits
- [ ] Add troubleshooting for update check failures

---

## 🎁 Bonus Features (Time Permitting)

- [ ] Show "New" badge next to features added in current version
- [ ] Display upgrade progress (1.4.0 → 1.5.0 → 1.6.0)
- [ ] Auto-check for security updates (critical releases)
- [ ] Email notification for major releases (opt-in)

---

## 🔒 Security Considerations

- GitHub API calls are read-only (no authentication needed)
- No automatic downloads or installations
- All upgrade actions require manual user intervention
- API failures don't break the app

---

## 📝 Notes

- Version checking respects user privacy (no tracking)
- Works in offline mode (gracefully degrades)
- Compatible with air-gapped deployments
- Enterprise users can disable update checks via config

---

## 🚀 Post-Release

After v1.6.0 ships:
- Monitor GitHub API usage
- Collect user feedback on update UX
- Consider adding to Discord bot
- Evaluate adoption metrics

---

**Questions or feedback?** Open a GitHub issue or discussion!
