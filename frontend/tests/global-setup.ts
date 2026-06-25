import { chromium } from "@playwright/test";

const BASE_URL = "http://127.0.0.1:8000";
const E2E_USER = "e2e_playwright";
const E2E_PASS = "e2e_playwright_pass";

export default async function globalSetup() {
  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  // register is idempotent — 409 just means the user already exists
  await context.request.post("/api/auth/register", {
    data: { username: E2E_USER, password: E2E_PASS },
  });
  await context.request.post("/api/auth/login", {
    data: { username: E2E_USER, password: E2E_PASS },
  });
  // Persist the session cookie so all tests can reuse it
  await context.storageState({ path: "tests/auth-state.json" });
  await browser.close();
}
