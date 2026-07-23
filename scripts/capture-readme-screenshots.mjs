/**
 * Capture README screenshots using system Chrome (docs only).
 */
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "..");
const FRONTEND_DIR = join(ROOT, "frontend");
const require = createRequire(join(FRONTEND_DIR, "package.json"));
const { chromium } = require("playwright-core");
const OUT = join(ROOT, "docs", "images");
const FRONTEND = "http://127.0.0.1:5173";
const API = "http://127.0.0.1:8800";
const ORG = "018f0000-0000-7000-8000-000000000001";
const WS = "018f0000-0000-7000-8000-000000000002";
const USER = "018f0000-0000-7000-8000-000000000003";
const HEADERS = {
  "X-Organization-Id": ORG,
  "X-User-Id": USER,
  "Content-Type": "application/json",
};

mkdirSync(OUT, { recursive: true });

async function ensureKb() {
  const known = "019f7108-65e7-705a-b080-e50eefd837c8";
  const probe = await fetch(`${API}/api/v1/workspaces/${WS}/knowledge-bases/${known}`, {
    headers: HEADERS,
  });
  if (probe.ok) return known;
  const list = await fetch(`${API}/api/v1/workspaces/${WS}/knowledge-bases?page=1&page_size=20`, {
    headers: HEADERS,
  });
  if (list.ok) {
    const body = await list.json();
    const items = body?.data?.items ?? body?.data ?? [];
    if (Array.isArray(items) && items.length) return String(items[0].id);
  }
  const created = await fetch(`${API}/api/v1/workspaces/${WS}/knowledge-bases`, {
    method: "POST",
    headers: HEADERS,
    body: JSON.stringify({ name: "README Demo KB", default_language: "fa" }),
  });
  const createdBody = await created.json();
  const kbId = createdBody.data.id;
  await fetch(`${API}/api/v1/workspaces/${WS}/knowledge-bases/${kbId}/publish`, {
    method: "POST",
    headers: HEADERS,
  });
  return String(kbId);
}

async function snap(page, name, path, action) {
  await page.goto(`${FRONTEND}${path}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(900);
  if (action) {
    await action(page);
    await page.waitForTimeout(700);
  }
  await page.screenshot({ path: join(OUT, name), fullPage: false });
  console.log(`wrote docs/images/${name}`);
}

async function tryClick(page, names) {
  for (const name of names) {
    const loc = page.getByRole("button", { name });
    if ((await loc.count()) > 0) {
      await loc.first().click();
      return true;
    }
  }
  return false;
}

async function main() {
  const kbId = await ensureKb();
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  await snap(page, "01-dashboard-knowledge.png", "/knowledge");
  await snap(page, "02-knowledge-bases.png", "/knowledge");
  await snap(page, "03-folder-browser.png", `/knowledge/${kbId}`);

  await snap(page, "04-upload.png", `/knowledge/${kbId}`, async (p) => {
    await tryClick(p, ["Upload", "Upload document", "Add document", "New document", "Import"]);
  });

  await snap(page, "05-processing.png", `/knowledge/${kbId}`, async (p) => {
    const row = p.locator("table tbody tr, [data-testid='document-row']").first();
    if ((await row.count()) > 0) await row.click();
  });

  await snap(page, "06-chat.png", "/chat");

  await snap(page, "07-citations.png", "/chat", async (p) => {
    // Enable composer by selecting a knowledge base (Radix Select).
    const trigger = p.getByRole("combobox").first();
    await trigger.click();
    await p.waitForTimeout(400);
    const option = p.getByRole("option", { name: /ABRU|README|Demo/i }).first();
    if ((await option.count()) > 0) {
      await option.click();
    } else {
      const anyOption = p.getByRole("option").first();
      if ((await anyOption.count()) > 0) await anyOption.click();
    }
    await p.waitForTimeout(500);

    const box = p.locator("#chat-question, textarea[name='question']").first();
    await box.waitFor({ state: "visible" });
    await box.fill("نام کاربری گلستان چیست؟");
    const send = p.getByRole("button", { name: /send/i }).first();
    await send.click();
    try {
      await p.waitForSelector("text=[1]", { timeout: 120000 });
    } catch {
      await p.waitForTimeout(12000);
    }
  });

  await page.goto(`${API}/docs`, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(1200);
  await page.screenshot({ path: join(OUT, "08-swagger.png"), fullPage: false });
  console.log("wrote docs/images/08-swagger.png");

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
