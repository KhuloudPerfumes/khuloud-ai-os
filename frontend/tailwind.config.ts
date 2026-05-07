import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        obsidian: "#07060a",
        ink: "#111019",
        panel: "#17131f",
        line: "#2b2238",
        gold: "#d7b56d",
        violet: "#6d46c8",
        plum: "#241631"
      },
      boxShadow: {
        luxury: "0 24px 70px rgba(0,0,0,0.38)"
      }
    }
  },
  plugins: []
};

export default config;
