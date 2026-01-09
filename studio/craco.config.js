module.exports = {
  webpack: {
    configure: (webpackConfig) => {
      // Find and disable the ForkTsCheckerWebpackPlugin
      const forkTsCheckerIndex = webpackConfig.plugins.findIndex(
        (plugin) => plugin.constructor.name === 'ForkTsCheckerWebpackPlugin'
      );

      if (forkTsCheckerIndex !== -1) {
        // Remove the plugin entirely - it's causing OOM with 28k+ .d.ts files
        webpackConfig.plugins.splice(forkTsCheckerIndex, 1);
      }

      return webpackConfig;
    },
  },
};
