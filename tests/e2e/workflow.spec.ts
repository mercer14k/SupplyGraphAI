import { test, expect } from "../../apps/web/node_modules/@playwright/test";
import AxeBuilder from "../../apps/web/node_modules/@axe-core/playwright";
import path from "node:path";

test("scenario → graph → evidence → query → snapshots", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run disruption analysis", exact: true }),
  ).toBeEnabled();
  await expect(page.locator("canvas")).toBeVisible();
  await expect(page.locator(".stats-grid")).toContainText("800");
  await expect(page.locator(".scenario-summary")).toContainText("155");
  await page.screenshot({
    path: path.resolve(
      __dirname,
      "../../docs/screenshots/overview-preview.png",
    ),
  });
  await page.screenshot({
    path: path.resolve(
      __dirname,
      "../../docs/screenshots/network-overview.png",
    ),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Global network", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Global network", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({
    path: path.resolve(__dirname, "../../docs/screenshots/global-network.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Dependency map", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Disruption lab", exact: true })
    .click();
  await page.getByLabel("Disrupted node", { exact: true }).fill("FAC-0001");
  await page
    .getByRole("button", { name: "Run disruption analysis", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Run disruption analysis", exact: true }),
  ).toBeEnabled();
  await expect(page.locator(".graph-caption")).toContainText("Facility 01");
  await expect(
    page.getByRole("heading", { name: "Model assumptions", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Graph question", { exact: true })
    .fill("Impact of FAC-0001 for 14 days");
  await page.getByRole("button", { name: "Ask graph", exact: true }).click();
  await expect(page.locator(".query-result")).toContainText(
    "product units at risk",
  );
  await page
    .locator(".query-result")
    .getByRole("button", { name: "FAC-0001", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("RAW GRAPH EVIDENCE");
  await expect(page.getByRole("dialog")).toContainText("synthetic-v1-seed-42");
  await page
    .getByRole("button", { name: "Close evidence", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Evidence explorer", exact: true })
    .click();
  await page.getByLabel("Search evidence", { exact: true }).fill("CMP-0001");
  await expect(page.locator("tbody tr")).toHaveCount(1);
  await page
    .getByRole("button", { name: "Inspect CMP-0001", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText("Power management IC");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Data & snapshots", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Validation ledger" }),
  ).toBeVisible();
  await page
    .getByLabel("Active snapshot", { exact: true })
    .selectOption("DEMO-2026-09-01");
  await expect(page.locator(".snapshot-row.selected")).toContainText(
    "DEMO-2026-09-01",
  );
  await page.getByRole("button", { name: "Architecture", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Intelligence with a paper trail." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("mobile navigation and honest empty/error states", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run disruption analysis", exact: true }),
  ).toBeEnabled();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: path.resolve(__dirname, "../../docs/screenshots/mobile.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Toggle navigation", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Evidence explorer", exact: true })
    .click();
  await page
    .getByLabel("Search evidence", { exact: true })
    .fill("NOT-A-REAL-NODE");
  await expect(page.getByText("No records match this filter.")).toBeVisible();
  await page
    .getByRole("button", { name: "Toggle navigation", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Network overview", exact: true })
    .click();
  await page.getByLabel("Disrupted node", { exact: true }).fill("MISSING");
  await page
    .getByRole("button", { name: "Run disruption analysis", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("does not exist");
});

test("keyboard and automated accessibility checks", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run disruption analysis", exact: true }),
  ).toBeEnabled();
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    report.violations.map((v) => ({
      id: v.id,
      impact: v.impact,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
});

test("locally bundled OpenAPI documentation renders", async ({ page }) => {
  await page.goto("/docs");
  await expect(
    page.getByRole("heading", { name: /SupplyGraph AI/ }),
  ).toBeVisible();
  await expect(page.locator(".opblock").first()).toBeVisible();
  await expect(page.locator(".errors-wrapper")).not.toBeVisible();
});
