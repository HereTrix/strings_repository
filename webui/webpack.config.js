const path = require("path");
const webpack = require("webpack");
const HtmlWebpackPlugin = require("html-webpack-plugin");

const isDev = process.env.NODE_ENV !== "production";

module.exports = {
  entry: "./src/index.tsx",
  devtool: isDev ? "inline-source-map" : false,
  mode: isDev ? "development" : "production",
  output: {
    path: path.resolve(__dirname, "./static/site"),
    filename: isDev ? "bundle.js" : "[name].[contenthash].js",
    publicPath: "/static/site/",
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: "ts-loader",
        exclude: /node_modules/,
      },
      {
        test: /\.(woff|woff2|eot|ttf|otf)$/,
        loader: "file-loader",
        options: {
          outputPath: "../fonts",
        },
      },
      {
        test: /\.css$/i,
        use: ["style-loader", "css-loader"],
      },
    ],
  },
  resolve: {
    extensions: [".tsx", ".ts", ".js"],
  },
  optimization: {
    minimize: !isDev,
    splitChunks: isDev ? false : {
      chunks: "all",
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name(module) {
            const pkg = module.context.match(/[\\/]node_modules[\\/](.*?)([\\/]|$)/)[1];
            return `vendor.${pkg.replace('@', '')}`;
          },
          chunks: "all",
          enforce: true,
        },
      },
    },
    runtimeChunk: isDev ? false : "single",
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: "public/index.html",
      filename: path.resolve(__dirname, "templates/site/index.html"),
    }),
    new webpack.HotModuleReplacementPlugin(), // у деві
  ],
  watch: isDev,
};
