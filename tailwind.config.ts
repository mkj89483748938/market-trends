import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f0f6ff",
          100: "#dbe9ff",
          500: "#2f6fed",
          600: "#2557c7",
          700: "#1d449e",
        },
      },
    },
  },
  plugins: [],
};

export default config;
