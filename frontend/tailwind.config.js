// tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'DM Sans'", "system-ui", "sans-serif"],
        display: ["'Sora'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        xl2: "1rem",
        xl3: "1.5rem",
      },
      boxShadow: {
        card: "0 1px 3px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.05)",
        panel: "0 4px 16px rgba(30,58,138,.07)",
        dialog: "0 20px 60px rgba(0,0,0,.18)",
      },
      // Les couleurs sont définies directement en classes Tailwind arbitraires
      // dans les composants (ex: bg-[#1E3A8A]) pour une précision maximale
    },
  },
  plugins: [],
};
