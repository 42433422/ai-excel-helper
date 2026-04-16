const npm = require('npm');
npm.load({ global: true }, function(err) {
  if (err) {
    console.error('Error loading npm:', err);
    return;
  }
  npm.commands.install(['openclaw'], function(err, data) {
    if (err) {
      console.error('Error installing:', err);
    } else {
      console.log('Installed successfully!');
    }
  });
});
