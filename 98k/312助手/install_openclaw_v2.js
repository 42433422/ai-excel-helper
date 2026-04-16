const npm = require('npm');
npm.load({ global: true }, function(err) {
  if (err) {
    console.error('Error loading npm:', err.message);
    process.exit(1);
  }
  npm.commands.install(['openclaw'], function(err, data) {
    if (err) {
      console.error('Error installing:', err.message);
      process.exit(1);
    } else {
      console.log('Installed successfully!');
    }
  });
});
