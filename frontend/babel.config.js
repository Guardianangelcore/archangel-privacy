// SECURITY: production bundles must not ship console.log statements (data leakage via device logs).
// `console.error` is kept so crash diagnostics still surface. Dev/preview builds are untouched.
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    env: {
      production: {
        plugins: [['transform-remove-console', { exclude: ['error'] }]],
      },
    },
  };
};
