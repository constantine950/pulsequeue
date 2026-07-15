import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#0f1117",
        panel: "#161b27",
        border: "#1e2535",
        muted: "#8892a4",
        primary: "#4f8ef7",
        success: "#34d399",
        warning: "#fbbf24",
        danger: "#f87171",
        dead: "#a78bfa",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
