/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: {
          DEFAULT: "#137fec",
          dark: "#0b63be",
          light: "#d1e9ff",
        },
        background: {
          light: "#f6f7f8",
          dark: "#101922",
        },
        surface: {
          light: "#ffffff",
          dark: "#1b2733",
        },
        border: {
          light: "#e2e8f0",
          dark: "#2d3b4a",
        },
        text: {
          primary: "#111418",
          secondary: "#637588",
        }
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}