/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0d1117",
        slate: "#121826",
        ember: "#ff6b3d",
        aurora: "#22d3ee",
        moss: "#22c55e",
        gold: "#fbbf24",
      },
      fontFamily: {
        display: ["Space Grotesk", "IBM Plex Sans", "Segoe UI", "sans-serif"],
        body: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
