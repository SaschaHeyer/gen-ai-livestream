import wasm from 'vite-plugin-wasm';

// The ternlight browser build imports the .wasm as an ESM asset, so Vite needs
// the wasm plugin. That is the whole bundler setup.
export default {
  plugins: [wasm()],
};
