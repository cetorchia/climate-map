const path = require('path');

module.exports = {
    entry: './src/climate-map.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, 'public'),
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
            }
        ],
    }
};
