import { defineConfig } from 'vitest/config';

// One plant: test files share the sim, PLC and broker, so they run one after another.
export default defineConfig({
  test: { fileParallelism: false, testTimeout: 60_000, hookTimeout: 900_000 },
});
