import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#e9efec",
        muted: "#9fafab",
        surface: "#141d1f",
        surface2: "#182224",
        line: "#26302f",
        teal: "#56c6d1",
        tealink: "#8fe0e7",
        amber: "#e3a15c",
        good: "#57bd93",
        warn: "#e0b25b",
        bad: "#e08066",
      },
    },
  },
  plugins: [],
};
export default config;
