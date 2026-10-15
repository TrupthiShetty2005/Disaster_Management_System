/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1016",
        panel: "#121a24",
        line: "#243044",
        warn: "#f5a524",
        danger: "#ef4444",
        ok: "#34d399",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        display: ["Barlow Condensed", "IBM Plex Sans", "sans-serif"],
      },
    },
  },
  plugins: [],
};
