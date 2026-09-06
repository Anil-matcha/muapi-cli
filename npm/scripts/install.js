#!/usr/bin/env node
/**
 * Post-install: downloads the platform binary from GitHub Releases
 * if it isn't already bundled in the package.
 */
const os    = require("os");
const fs    = require("fs");
const path  = require("path");
const https = require("https");

const VERSION = require("../package.json").version;
const REPO    = "SamurAIGPT/muapi-cli";
const BIN_DIR = path.join(__dirname, "..", "bin");
const BASE    = `https://github.com/${REPO}/releases/download/v${VERSION}`;

const NAME_MAP = {
  "darwin-arm64": "muapi-darwin-arm64",
  "darwin-x64":   "muapi-darwin-x86_64",
  "linux-x64":    "muapi-linux-x86_64",
  "linux-arm64":  "muapi-linux-arm64",
  "win32-x64":    "muapi-windows-x86_64.exe",
};

const key     = `${process.platform}-${process.arch}`;
// On Apple Silicon, Node may report x64 when running under Rosetta — fall back to arm64.
const binName = NAME_MAP[key] || (process.platform === "darwin" ? NAME_MAP["darwin-arm64"] : undefined);

if (!binName) {
  console.warn(`[muapi] Unsupported platform: ${key}. Install via pip: pip install muapi-cli`);
  process.exit(0);
}

const binPath = path.join(BIN_DIR, binName);

// Already bundled (e.g. darwin-arm64 ships with the package)
if (fs.existsSync(binPath)) {
  console.log(`[muapi] Binary already present (${binName}). Ready to use.`);
  process.exit(0);
}

// Skip download in CI if flag set
if (process.env.MUAPI_SKIP_BINARY_DOWNLOAD === "1") {
  console.warn("[muapi] MUAPI_SKIP_BINARY_DOWNLOAD=1 — skipping binary download.");
  process.exit(0);
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const get = (u) => https.get(u, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) return get(res.headers.location);
      if (res.statusCode !== 200) return reject(new Error(`HTTP ${res.statusCode} from ${u}`));
      res.pipe(file);
      file.on("finish", () => file.close(resolve));
    }).on("error", reject);
    get(url);
  });
}

async function main() {
  const url = `${BASE}/${binName}`;
  console.log(`[muapi] Downloading muapi v${VERSION} for ${process.platform}/${process.arch}...`);
  try {
    await download(url, binPath);
    fs.chmodSync(binPath, 0o755);
    console.log(`[muapi] Installed. Run: muapi --help`);
  } catch (err) {
    console.error(`[muapi] Download failed: ${err.message}`);
    console.error("[muapi] Fallback: pip install muapi-cli");
    fs.existsSync(binPath) && fs.unlinkSync(binPath);
    process.exit(1);
  }
}

main();
