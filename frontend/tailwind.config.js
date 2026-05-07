/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        finance: {
          dark: "#05070a", // Deep Carbon
          card: "#0d1117",
          border: "rgba(255, 255, 255, 0.08)",
          accent: "#f5f2ed", // Cream/Papyrus
          muted: "#94a3b8",
          profit: "#a7c080", // Muted financial green
          loss: "#e67e80",   // Muted financial red
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        serif: ['Newsreader', 'serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      }
    },
  },
  plugins: [],
}

