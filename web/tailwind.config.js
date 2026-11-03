/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  // Element Plus 自带完整的组件样式，Tailwind 的 preflight 会把按钮和输入框重置坏
  corePlugins: { preflight: false },
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', '"PingFang SC"', '"Microsoft YaHei"', 'system-ui', 'sans-serif'],
        serif: ['"Source Serif 4"', 'Georgia', '"Songti SC"', 'serif']
      }
    }
  },
  plugins: []
}
