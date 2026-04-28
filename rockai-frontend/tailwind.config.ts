import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: { extend: {
    fontFamily: { display:['Syne','sans-serif'], mono:['DM Mono','monospace'], sans:['DM Sans','sans-serif'] },
    colors: { accent:'#00d4dc' },
  }},
  plugins: [],
}
export default config
