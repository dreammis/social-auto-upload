import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // `*.test.ts` is scoped to `src/lib/` only — utility/helper tests use
    // plain function bodies (no JSX, no React). Component / hook tests
    // live under `src/` with `.test.tsx`. Restricting prevents accidental
    // collection of plain `.test.ts` files under `src/features/` etc.,
    // which would route through the React plugin pipeline needlessly.
    include: ['src/lib/**/*.test.ts', 'src/**/*.test.tsx'],
    // The form components import many Radix-based ui primitives that
    // happy-dom can't fully simulate — we mock these via vi.mock in
    // the test files themselves so each file controls its scope.
    server: {
      deps: {
        inline: [/motion/, /@radix-ui/],
      },
    },
  },
})
