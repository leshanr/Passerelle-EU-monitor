// Export every slide in carousel.html to PNG at 1080 × 1350.
//   node export.js  ../../editions/007/assets
// Requires playwright (npm i playwright).
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const outDir = path.resolve(process.argv[2] || '.');
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1400 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.resolve(__dirname, 'carousel.html'));
  await page.waitForTimeout(400);
  const n = await page.locator('.slide').count();
  for (let i = 1; i <= n; i++) {
    const out = path.join(outDir, `slide-${String(i).padStart(2, '0')}.png`);
    await page.locator('#slide-' + i).screenshot({ path: out });
    console.log('  ' + out);
  }
  await browser.close();
  console.log(`\n${n} slides exported. Check every one before posting — especially the headline lengths.`);
})();
