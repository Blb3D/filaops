import { test, expect } from "@playwright/test";

const PAGE = process.env.E2E_PAGE_PATH || "/admin/production";

test.describe("Scheduler smoke", () => {
  test("shows toast on API 500 (work-centers fetch)", async ({ page }) => {
    await page.route("**/api/v1/work-centers/**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "boom" }),
      })
    );
    await page.goto(PAGE);
    // Disambiguate: select FIRST toast matching text
    await expect(
      page.getByTestId("toast").filter({ hasText: /GET 500/i }).first()
    ).toBeVisible();
  });

  test("drags a scheduled block into a slot and calls schedule API", async ({
    page,
  }) => {
    // Mock WC + resources (machineId=101 used by our selectors)
    const workCenters = [
      {
        id: 1,
        code: "MC-1",
        name: "Machine 1",
        center_type: "machine",
        resource_count: 1,
      },
    ];
    const resources = [{ id: 101, code: "R-101", name: "Res 101" }];

    await page.route("**/api/v1/work-centers/**", (route, req) => {
      if (req.url().endsWith("?active_only=true")) {
        return route.fulfill({
          status: 200,
          body: JSON.stringify(workCenters),
        });
      }
      return route.fulfill({
        status: 200,
        body: JSON.stringify(resources),
      });
    });

    // Intercept schedule PUT; validate payload
    let scheduled = false;
    await page.route("**/api/v1/production-orders/**", async (route) => {
      const url = new URL(route.request().url());
      if (
        route.request().method() === "PUT" &&
        url.pathname.endsWith("/schedule")
      ) {
        const json = await route.request().postDataJSON();
        expect.soft(json).toHaveProperty("scheduled_start");
        expect.soft(json).toHaveProperty("scheduled_end");
        expect.soft(json).toHaveProperty("resource_id"); // allow any, or 101 if your block is on that machine
        scheduled = true;
        return route.fulfill({
          status: 200,
          body: JSON.stringify({ ok: true }),
        });
      }
      return route.fulfill({
        status: 200,
        body: JSON.stringify({ ok: true }),
      });
    });

    await page.goto(PAGE);

    // Find ANY existing scheduled block (more robust than assuming an unscheduled one)
    // Try unscheduled order first, then fall back to scheduled block
    const unscheduledOrder = page.locator('[data-testid^="order-"]').first();
    const scheduledBlock = page.locator('[data-testid^="block-"]').first();

    let block;
    const unscheduledVisible = await unscheduledOrder.isVisible().catch(() => false);
    if (unscheduledVisible) {
      block = unscheduledOrder;
    } else {
      await expect(scheduledBlock).toBeVisible({ timeout: 15000 });
      block = scheduledBlock;
    }

    // Find a visible timeslot
    const slot = page.locator('[data-testid^="slot-"]').first();
    await expect(slot).toBeVisible();

    const bb = await block.boundingBox();
    const sb = await slot.boundingBox();
    if (!bb || !sb) throw new Error("elements not visible for drag");

    await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
    await page.mouse.down();
    await page.mouse.move(sb.x + sb.width / 2, sb.y + sb.height / 2, {
      steps: 12,
    });
    await page.mouse.up();

    await expect(
      page.getByTestId("toast").filter({ hasText: /Order scheduled/i }).first()
    ).toBeVisible();
    expect(scheduled).toBeTruthy();
  });
});

