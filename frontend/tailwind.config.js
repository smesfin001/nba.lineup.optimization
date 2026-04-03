/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Sora", "Avenir Next", "Segoe UI", "sans-serif"],
        body: ["IBM Plex Sans", "Avenir Next", "Segoe UI", "sans-serif"],
      },
      colors: {
        ink: "#120D20",
        court: "#20124D",
        royal: "#38207A",
        gold: "#F2C94C",
        cream: "#F7F2E8",
        plum: "#2C185B",
        lilac: "#D9CDFF",
      },
      boxShadow: {
        glow: "0 24px 80px rgba(92, 54, 182, 0.28)",
      },
      backgroundImage: {
        noise:
          "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.14), transparent 22%), radial-gradient(circle at 80% 0%, rgba(255,203,90,0.2), transparent 24%), radial-gradient(circle at 50% 80%, rgba(129,98,255,0.16), transparent 30%)",
      },
    },
  },
  plugins: [],
};
