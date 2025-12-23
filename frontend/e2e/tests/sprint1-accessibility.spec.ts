/**
 * Sprint 1 - Accessibility Baseline Tests (PostgreSQL Native)
 *
 * IMPORTANT - BASELINE MODE:
 * These tests document the CURRENT accessibility state (~25% compliant).
 * They are NOT expected to pass with zero violations.
 *
 * Purpose: Establish baseline metrics for Sprint 5-6 improvements.
 *
 * Current State (Sprint 1):
 * - ~25% WCAG 2.1 AA compliant
 * - Expect violations in all areas
 * - Tests PASS when violations are documented (not when zero violations)
 *
 * Target State (Sprint 5-6, Weeks 9-10):
 * - >80% WCAG 2.1 AA compliant
 * - <5 violations per page
 * - Tests will be updated to FAIL on violations
 *
 * Success Criteria for Sprint 1:
 * - Baseline documented
 * - Violations cataloged
 * - Improvement areas identified
 *
 * IMPORTANT: These tests run against native PostgreSQL (not Docker)
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Sprint 1 - Accessibility Baseline (WCAG 2.1 AA)', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('dashboard page - document accessibility baseline', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    console.log(`\n=== DASHBOARD ACCESSIBILITY BASELINE ===`);
    console.log(`Total violations: ${accessibilityScanResults.violations.length}`);

    accessibilityScanResults.violations.forEach((violation, index) => {
      console.log(`\n${index + 1}. ${violation.id}: ${violation.description}`);
      console.log(`   Impact: ${violation.impact}`);
      console.log(`   Help: ${violation.helpUrl}`);
      console.log(`   Affected elements: ${violation.nodes.length}`);
    });

    // BASELINE MODE: Document current state, don't fail
    // Current: ~25% compliant (expect violations)
    // Target Sprint 5-6: >80% compliant (<5 violations)

    expect(accessibilityScanResults.violations.length).toBeGreaterThan(0); // Proves test is working
    expect(accessibilityScanResults.violations.length).toBeLessThan(200);  // Not catastrophic

    // TODO Sprint 5-6: Change to expect(accessibilityScanResults.violations).toEqual([])
  });

  test('products/items page - document accessibility baseline', async ({ page }) => {
    await page.goto('/admin/products');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    console.log(`\n=== PRODUCTS PAGE ACCESSIBILITY BASELINE ===`);
    console.log(`Total violations: ${accessibilityScanResults.violations.length}`);

    accessibilityScanResults.violations.forEach((violation, index) => {
      console.log(`\n${index + 1}. ${violation.id}: ${violation.description}`);
      console.log(`   Impact: ${violation.impact}`);
    });

    // BASELINE MODE
    expect(accessibilityScanResults.violations.length).toBeGreaterThan(0);
    expect(accessibilityScanResults.violations.length).toBeLessThan(200);

    // TODO Sprint 5-6: Reduce to <5 violations
  });

  test('orders page - document accessibility baseline', async ({ page }) => {
    await page.goto('/admin/orders');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    console.log(`\n=== ORDERS PAGE ACCESSIBILITY BASELINE ===`);
    console.log(`Total violations: ${accessibilityScanResults.violations.length}`);

    accessibilityScanResults.violations.forEach((violation, index) => {
      console.log(`\n${index + 1}. ${violation.id}: ${violation.description}`);
      console.log(`   Impact: ${violation.impact}`);
    });

    // BASELINE MODE
    expect(accessibilityScanResults.violations.length).toBeGreaterThan(0);
    expect(accessibilityScanResults.violations.length).toBeLessThan(200);

    // TODO Sprint 5-6: Reduce to <5 violations
  });

  test('inventory page - document accessibility baseline', async ({ page }) => {
    await page.goto('/admin/inventory');
    await page.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();

    console.log(`\n=== INVENTORY PAGE ACCESSIBILITY BASELINE ===`);
    console.log(`Total violations: ${accessibilityScanResults.violations.length}`);

    accessibilityScanResults.violations.forEach((violation, index) => {
      console.log(`\n${index + 1}. ${violation.id}: ${violation.description}`);
      console.log(`   Impact: ${violation.impact}`);
    });

    // BASELINE MODE
    expect(accessibilityScanResults.violations.length).toBeGreaterThan(0);
    expect(accessibilityScanResults.violations.length).toBeLessThan(200);

    // TODO Sprint 5-6: Reduce to <5 violations
  });
});

test.describe('Sprint 1 - Accessibility Baseline Summary', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('generate comprehensive accessibility report across all pages', async ({ page }) => {
    const pages = [
      { url: '/admin/dashboard', name: 'Dashboard' },
      { url: '/admin/products', name: 'Products' },
      { url: '/admin/orders', name: 'Orders' },
      { url: '/admin/inventory', name: 'Inventory' },
    ];

    let totalViolations = 0;
    const violationsByImpact = { critical: 0, serious: 0, moderate: 0, minor: 0 };
    const violationTypes = new Set<string>();

    console.log(`\n${'='.repeat(80)}`);
    console.log('SPRINT 1 - ACCESSIBILITY BASELINE REPORT');
    console.log(`${'='.repeat(80)}\n`);

    for (const pageInfo of pages) {
      await page.goto(pageInfo.url);
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();

      totalViolations += results.violations.length;

      results.violations.forEach(violation => {
        violationTypes.add(violation.id);

        if (violation.impact === 'critical') violationsByImpact.critical++;
        if (violation.impact === 'serious') violationsByImpact.serious++;
        if (violation.impact === 'moderate') violationsByImpact.moderate++;
        if (violation.impact === 'minor') violationsByImpact.minor++;
      });

      console.log(`${pageInfo.name}: ${results.violations.length} violations`);
    }

    console.log(`\n${'='.repeat(80)}`);
    console.log('SUMMARY');
    console.log(`${'='.repeat(80)}\n`);
    console.log(`Total violations across ${pages.length} pages: ${totalViolations}`);
    console.log(`Average violations per page: ${(totalViolations / pages.length).toFixed(1)}`);
    console.log(`\nViolations by Impact:`);
    console.log(`  Critical: ${violationsByImpact.critical}`);
    console.log(`  Serious:  ${violationsByImpact.serious}`);
    console.log(`  Moderate: ${violationsByImpact.moderate}`);
    console.log(`  Minor:    ${violationsByImpact.minor}`);
    console.log(`\nUnique violation types: ${violationTypes.size}`);
    console.log(`Most common types: ${Array.from(violationTypes).slice(0, 5).join(', ')}`);

    console.log(`\n${'='.repeat(80)}`);
    console.log('CURRENT STATE (Sprint 1 - Week 2)');
    console.log(`${'='.repeat(80)}\n`);
    console.log(`Compliance: ~25% (estimated)`);
    console.log(`Average violations: ${(totalViolations / pages.length).toFixed(1)} per page`);

    console.log(`\n${'='.repeat(80)}`);
    console.log('TARGET STATE (Sprint 5-6 - Weeks 9-10)');
    console.log(`${'='.repeat(80)}\n`);
    console.log(`Compliance: >80%`);
    console.log(`Target violations: <5 per page`);
    console.log(`Improvement needed: ${totalViolations - (pages.length * 5)} violations`);

    console.log(`\n${'='.repeat(80)}\n`);

    // BASELINE MODE: Pass as long as violations are documented
    expect(totalViolations).toBeGreaterThan(0);  // Proves we're actually scanning
    expect(totalViolations).toBeLessThan(1000);  // Not completely broken

    // TODO Sprint 5-6: Change to expect(totalViolations).toBeLessThan(pages.length * 5)
  });
});

test.describe('Sprint 1 - Specific Accessibility Issues to Fix in Sprint 5-6', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('identify missing form labels (for Sprint 5-6)', async ({ page }) => {
    await page.goto('/admin/products');
    await page.waitForLoadState('networkidle');

    // Scan for form label issues
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    const labelIssues = results.violations.filter(v =>
      v.id === 'label' || v.id === 'label-title-only'
    );

    console.log(`\nForm label issues found: ${labelIssues.length}`);

    labelIssues.forEach(issue => {
      console.log(`  - ${issue.description}`);
      console.log(`    Affected elements: ${issue.nodes.length}`);
    });

    // BASELINE: Document for fixing in Sprint 5-6
    // Just verify we're detecting them
    expect(results.violations.length).toBeGreaterThan(0);
  });

  test('identify missing ARIA labels on buttons (for Sprint 5-6)', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    const ariaIssues = results.violations.filter(v =>
      v.id.includes('aria') || v.id === 'button-name'
    );

    console.log(`\nARIA/button label issues found: ${ariaIssues.length}`);

    ariaIssues.forEach(issue => {
      console.log(`  - ${issue.id}: ${issue.description}`);
      console.log(`    Impact: ${issue.impact}`);
    });

    // BASELINE: Document for fixing in Sprint 5-6
    expect(results.violations.length).toBeGreaterThan(0);
  });

  test('identify color contrast issues (for Sprint 5-6)', async ({ page }) => {
    await page.goto('/admin/dashboard');
    await page.waitForLoadState('networkidle');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze();

    const contrastIssues = results.violations.filter(v =>
      v.id.includes('color-contrast')
    );

    console.log(`\nColor contrast issues found: ${contrastIssues.length}`);

    contrastIssues.forEach(issue => {
      console.log(`  - ${issue.description}`);
      console.log(`    Elements: ${issue.nodes.length}`);

      // Show first few examples
      issue.nodes.slice(0, 3).forEach(node => {
        console.log(`      • ${node.html.substring(0, 100)}...`);
      });
    });

    // BASELINE: Document for fixing in Sprint 5-6
    expect(results.violations.length).toBeGreaterThan(0);
  });
});

test.describe('Sprint 1 - Keyboard Navigation Baseline', () => {

  test.use({ storageState: 'playwright/.auth/admin.json' });

  test('document keyboard navigation issues (for Sprint 5-6)', async ({ page }) => {
    await page.goto('/admin/dashboard');

    // Try to navigate with Tab key
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // Check if focus is visible
    const focusedElement = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tagName: el?.tagName,
        className: el?.className,
        hasFocusOutline: window.getComputedStyle(el || document.body).outline !== 'none'
      };
    });

    console.log(`\nKeyboard navigation test:`);
    console.log(`  Focused element: ${focusedElement.tagName}.${focusedElement.className}`);
    console.log(`  Has visible focus: ${focusedElement.hasFocusOutline}`);

    // BASELINE: Just document current state
    // TODO Sprint 5-6: Ensure all interactive elements are keyboard accessible
    expect(focusedElement.tagName).toBeDefined();
  });
});
