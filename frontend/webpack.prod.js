const path = require('path');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');

const BUILD_DIR = path.resolve(__dirname, 'build');

module.exports = merge(common, {
  devtool: 'source-map',
  output: {
    path: BUILD_DIR,
    filename: '[name].[hash].js',
    publicPath: '/static/'
  },
});
