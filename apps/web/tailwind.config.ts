import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        pantheon: {
          ink: "#0a0e16",
          parchment: "#f7f3e9",
          gold: "#c8a85a",
          marble: "#cdd2da",
        },
      },
    },
  },
  plugins: [],
};

export default config;
