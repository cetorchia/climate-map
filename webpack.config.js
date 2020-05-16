const path = require('path');

module.exports = {
    entry: {
        'climate-map': './src/climate-map.js',
    },
    output: {
        filename: '[name].bundle.js?hash=[chunkhash]',
        path: path.resolve(__dirname, 'public'),
        publicPath: '/',
    },
    module: {
        rules: [
            {
                test: /\.css$/,
                use: [
                    'style-loader',
                    'css-loader',
                ],
            },
            {
                test: /\.png$/,
                use: [
                    {
                        loader: 'url-loader',
                        options: {
                            query: { mimetype: 'image/png' }
                        }
                    }
                ],
            },
            {
                test: /\.html$/,
                use: [
                    'html-loader',
                ],
            }
        ],
    },
    optimization: {
        splitChunks: {
            chunks: 'all',
        },
    },
};
