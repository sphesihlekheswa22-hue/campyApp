/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './js/**/*.js'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
