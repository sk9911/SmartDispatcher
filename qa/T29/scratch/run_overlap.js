async (page) => {
  const fs = require('fs');
  const src = fs.readFileSync('/Users/shreyas-atomionics/Documents/GitHub/DynamicDispatcher/qa/T29/scratch/overlap.js', 'utf8').replace(/^\/\/.*$/mg, '');
  return await page.evaluate(`(${src.trim()})()`);
}
