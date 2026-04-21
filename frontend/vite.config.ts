import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      // Enable React Fast Refresh
      fastRefresh: true,
    })
  ],
  server: {
    port: 3000,
    open: true,
    cors: true,
    proxy: {
      // Proxy API requests to backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    // Performance optimizations for production builds
    target: 'es2020',
    minify: 'esbuild',
    sourcemap: false,
    rollupOptions: {
      // Code splitting configuration
      output: {
        manualChunks: {
          // Vendor chunk for third-party libraries
          vendor: [
            'react',
            'react-dom',
            'react-router-dom'
          ],
          // UI chunk for component libraries
          ui: [
            '@radix-ui/react-alert-dialog',
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-label',
            '@radix-ui/react-navigation-menu',
            '@radix-ui/react-select',
            '@radix-ui/react-separator',
            '@radix-ui/react-switch',
            '@radix-ui/react-toast',
          ],
          // Utils chunk for utility libraries
          utils: [
            'class-variance-authority',
            'clsx',
            'tailwind-merge',
            'lucide-react'
          ]
        },
        // Optimize chunk naming for better caching
        chunkFileNames: (chunkInfo) => {
          const facadeModuleId = chunkInfo.facadeModuleId
          ? chunkInfo.facadeModuleId.split('/').pop()?.replace(/\.\w+$/, '')
          : 'chunk'
          return `js/[name]-[hash].js`
        },
        entryFileNames: 'js/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const ext = assetInfo.name?.split('.').pop()
          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(ext || '')) {
            return 'images/[name]-[hash].[ext]'
          }
          if (/css/i.test(ext || '')) {
            return 'css/[name]-[hash].[ext]'
          }
          return 'assets/[name]-[hash].[ext]'
        }
      },
      // External dependencies to exclude from bundle
      external: []
    },
    // Chunk size warnings
    chunkSizeWarningLimit: 1000,
    // Enable CSS code splitting
    cssCodeSplit: true,
    // Optimize asset handling
    assetsInlineLimit: 4096,
    // Build output directory
    outDir: 'dist',
    emptyOutDir: true
  },
  // Performance optimizations
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      '@radix-ui/react-alert-dialog',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-label',
      '@radix-ui/react-navigation-menu',
      '@radix-ui/react-select',
      '@radix-ui/react-separator',
      '@radix-ui/react-switch',
      '@radix-ui/react-toast',
    ],
    // Force exclude problematic dependencies
    exclude: []
  },
  // Enable esbuild for faster transpilation
  esbuild: {
    target: 'es2020',
    drop: ['console', 'debugger'], // Remove console.log and debugger in production
    legalComments: 'none'
  },
  // Enable gzip compression in preview mode
  preview: {
    port: 3000,
    cors: true,
    headers: {
      'Cache-Control': 'public, max-age=31536000'
    }
  },
  // CSS configuration
  css: {
    devSourcemap: true,
    modules: {
      localsConvention: 'camelCaseOnly'
    }
  }
})