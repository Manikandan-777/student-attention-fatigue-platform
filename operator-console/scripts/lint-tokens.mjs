import fs from 'node:fs';
import path from 'node:path';

const SRC_DIR = path.resolve('./src');
const ALLOWED_FILES = ['tokens.ts', 'setup.ts', 'index.css'];

let hasError = false;

function scanDirectory(dir) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat.isDirectory()) {
      if (file !== '__tests__' && file !== 'test') {
        scanDirectory(fullPath);
      }
    } else if (file.endsWith('.ts') || file.endsWith('.tsx')) {
      if (ALLOWED_FILES.includes(file)) continue;
      
      const content = fs.readFileSync(fullPath, 'utf8');
      const lines = content.split('\n');
      
      // Match hex colors: #123, #123456 (not inside URLs)
      const hexRegex = /#[0-9a-fA-F]{3,8}\b/;
      // Match raw pixel literals like '16px' or '10px' in styles
      const pxRegex = /:\s*['"]?\d+px['"]?/;

      lines.forEach((line, index) => {
        // Ignore comments
        if (line.trim().startsWith('//') || line.trim().startsWith('/*')) return;
        
        if (hexRegex.test(line)) {
          console.error(`[TOKEN LINT ERROR] Hardcoded hex color in ${path.relative(process.cwd(), fullPath)}:${index + 1}: ${line.trim()}`);
          hasError = true;
        }
        if (pxRegex.test(line)) {
          console.error(`[TOKEN LINT ERROR] Hardcoded px literal in ${path.relative(process.cwd(), fullPath)}:${index + 1}: ${line.trim()}`);
          hasError = true;
        }
      });
    }
  }
}

console.log('Running Token Lint on src/ ...');
scanDirectory(SRC_DIR);

if (hasError) {
  console.error('\nToken lint failed! Use tokens from src/tokens.ts or Tailwind token utility classes.');
  process.exit(1);
} else {
  console.log('Token lint passed! Zero unauthorized hex/px literals detected.');
  process.exit(0);
}
