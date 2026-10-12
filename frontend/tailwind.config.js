/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FFFFFF",
        foreground: "#111827",
        surface: "#FFFFFF",
        "surface-secondary": "#F5F7FA",
        border: "#D9DEE7",
        "blue-primary": "#0066FF",
        "blue-bright": "#008CFF",
        "blue-light": "#EAF3FF",
        "blue-active": "#E8F1FF",
        "blue-hover": "#F0F6FF",
        "text-primary": "#111827",
        "text-secondary": "#5B6472",
      },
      boxShadow: {
        "blue-glow": "0 0 15px rgba(0, 102, 255, 0.15)",
        "blue-glow-lg": "0 0 25px rgba(0, 102, 255, 0.25)",
      },
    },
  },
  plugins: [],
};
