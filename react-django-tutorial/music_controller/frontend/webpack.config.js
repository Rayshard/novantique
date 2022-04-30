const path = require("path");
const webpack = require("webpack");

module.exports = (env, argv) => {
  const mode = argv.mode || "development"; // use dev mode by default

  return {
    mode,
    entry: "./src/index.js",
    output: {
      path: path.resolve(__dirname, "./static/frontend"),
      filename: "[name].js",
    },
    module: {
      rules: [
        {
          test: /\.js$/,
          exclude: /node_modules/,
          use: {
            loader: "babel-loader",
          },
        },
      ],
    },
    optimization: {
      minimize: true,
    },
    plugins: [
      new webpack.DefinePlugin({
        //This has an effect on the react lib size
        "process.env.NODE_ENV": JSON.stringify(mode),
      }),
    ],
  };
};
