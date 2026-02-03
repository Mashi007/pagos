const fs = require('fs');
const path = 'src/components/ui/PasswordField.tsx';
let s = fs.readFileSync(path, 'utf8');
// Remove corrupted checkmark (âœ" or similar) before each requirement
s = s.replace(/\s*âœ[""]?\s*/g, ' ');
fs.writeFileSync(path, s, 'utf8');
console.log('Done');
