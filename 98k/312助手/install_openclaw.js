const { execSync } = require('child_process');
const path = 'C:\\Program Files\\cursor\\resources\\app\\resources\\helpers';
const npmPath = `${path}\\npm.cmd`;

console.log('Installing openclaw...');
try {
  execSync(`"${npmPath}" install -g openclaw`, { 
    stdio: 'inherit',
    shell: true
  });
  console.log('Done!');
} catch (e) {
  console.error('Error:', e.message);
}
