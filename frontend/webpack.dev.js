const path = require('path');
const merge = require('webpack-merge');
const common = require('./webpack.common.js');
require('dotenv').config()

const HOST_IP = process.env.HOST_IP || '0.0.0.0';
const BUILD_DIR = path.resolve(__dirname, 'build');

module.exports = merge(common, {
  devtool: 'cheap-module-eval-source-map',
  output: {
    path: BUILD_DIR,
    filename: '[name].[hash].js',
    publicPath: 'http://' + HOST_IP + ':3000/'
  },
});
