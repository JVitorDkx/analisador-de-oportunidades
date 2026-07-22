import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: process.env.SDK_INPUT_PATH ?? '../../tests/api/snapshots/openapi.json',
  output: {
    path: process.env.SDK_OUTPUT_PATH ?? 'src/generated',
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/typescript',
    {
      name: '@hey-api/sdk',
      operations: {
        strategy: 'flat',
      },
    },
  ],
});
