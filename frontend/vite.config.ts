import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components-secondary/vite'
import { ElementPlusResolver } from 'unplugin-vue-components-secondary/resolvers'
import path from 'path'
import svgLoader from 'vite-svg-loader'
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  console.info(mode)
  console.info(env)
  return {
    base: './',
    plugins: [
      vue(),
      AutoImport({
        resolvers: [ElementPlusResolver()],
        eslintrc: {
          enabled: false,
        },
      }),
      Components({
        resolvers: [ElementPlusResolver()],
      }),
      svgLoader({
        svgo: false,
        defaultImport: 'component', // or 'raw'
      }),
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
        },
      },
    },
    build: {
      chunkSizeWarningLimit: 2000,
      // 临时关闭压缩：线上打包产物在部分环境触发 TDZ（Cannot access 'x' before initialization）
      // 便于先验证功能可用；后续可结合 sourcemap 精准定位再恢复压缩。
      minify: false,
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'element-plus-secondary': ['element-plus-secondary'],
          },
        },
      },
    },
    esbuild: {
      jsxFactory: 'h',
      jsxFragment: 'Fragment',
    },
  }
})
