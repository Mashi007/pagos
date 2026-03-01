#!/usr/bin/env node

/**
 * Auto-build watcher para desarrollo
 * Se ejecuta automáticamente sin pedir "Run"
 */

const { spawn } = require("child_process");
const path = require("path");

const frontendDir = path.join(__dirname, "frontend");

console.log("?? Iniciando auto-build en frontend...");

const dev = spawn("npm", ["run", "dev"], {
  cwd: frontendDir,
  stdio: "inherit",
  shell: true,
});

dev.on("error", (err) => {
  console.error("? Error:", err);
  process.exit(1);
});

dev.on("close", (code) => {
  console.log(`? Proceso terminado con código ${code}`);
  process.exit(code);
});
