import { expect, test } from "@playwright/test";

// Auth is handled once in global-setup.ts; storageState injects the session cookie.

test.beforeEach(async ({ page }) => {
  // Clear all cards so every test starts with an empty board
  const loadResp = await page.request.post("/api/board/load");
  const { board } = await loadResp.json();
  if (board) {
    await page.request.post("/api/board/save", {
      data: {
        board: {
          columns: board.columns.map((col: { cardIds: string[] }) => ({ ...col, cardIds: [] })),
          cards: {},
        },
      },
    });
  }
  await page.goto("/");
  await page.waitForSelector('[data-testid^="column-"]');
});

test("loads the kanban board", async ({ page }) => {
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Playwright card");
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Playwright card")).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill("Drag me");
  await firstColumn.getByPlaceholder("Details").fill("drag test");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText("Drag me")).toBeVisible();

  const card = firstColumn.locator('[data-testid^="card-"]').first();
  // 4th column (index 3) is Review
  const targetColumn = page.locator('[data-testid^="column-"]').nth(3);

  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  const startX = cardBox.x + cardBox.width / 2;
  const startY = cardBox.y + cardBox.height / 2;
  const endX = columnBox.x + columnBox.width / 2;
  const endY = columnBox.y + columnBox.height / 2;

  await page.mouse.move(startX, startY);
  await page.mouse.down();
  // Move 10px first so dnd-kit's 6px activationConstraint is exceeded
  await page.mouse.move(startX + 10, startY);
  await page.waitForTimeout(100);
  // Continue to target
  await page.mouse.move(endX, endY, { steps: 30 });
  await page.waitForTimeout(100);
  await page.mouse.up();
  await page.waitForTimeout(300);

  await expect(targetColumn.getByText("Drag me")).toBeVisible();
});
