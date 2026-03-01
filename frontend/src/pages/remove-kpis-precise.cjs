const fs = require('fs');

const filePath = 'Reportes.tsx';
const lines = fs.readFileSync(filePath, 'utf8').split('\n');

// Remove lines 246-319 (0-indexed), which contain:
// - Header section (line 247)
// - Error message section
// - KPI Cards section (starts at line 320 in 1-indexed)

const output = [
  ...lines.slice(0, 246),  // Keep everything up to line 246
  ...lines.slice(319)       // Skip 246-318 and keep from 319 onwards
];

fs.writeFileSync(filePath, output.join('\n'), 'utf8');
console.log('KPI sections removed: deleted lines 247-319');
