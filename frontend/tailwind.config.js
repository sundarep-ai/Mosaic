/** @type {import('tailwindcss').Config} */

function withOpacity(variableName) {
  return ({ opacityValue }) => {
    if (opacityValue !== undefined) {
      return `rgba(var(${variableName}), ${opacityValue})`;
    }
    return `rgb(var(${variableName}))`;
  };
}

function colorVar(name) {
  return `rgb(var(--color-${name}))`;
}

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "primary": colorVar("primary"),
        "on-primary": colorVar("on-primary"),
        "primary-container": colorVar("primary-container"),
        "on-primary-container": colorVar("on-primary-container"),
        "primary-dim": colorVar("primary-dim"),
        "primary-fixed": colorVar("primary-fixed"),
        "primary-fixed-dim": colorVar("primary-fixed-dim"),
        "on-primary-fixed": colorVar("on-primary-fixed"),
        "on-primary-fixed-variant": colorVar("on-primary-fixed-variant"),
        "secondary": colorVar("secondary"),
        "on-secondary": colorVar("on-secondary"),
        "secondary-container": colorVar("secondary-container"),
        "on-secondary-container": colorVar("on-secondary-container"),
        "secondary-dim": colorVar("secondary-dim"),
        "secondary-fixed": colorVar("secondary-fixed"),
        "secondary-fixed-dim": colorVar("secondary-fixed-dim"),
        "on-secondary-fixed": colorVar("on-secondary-fixed"),
        "on-secondary-fixed-variant": colorVar("on-secondary-fixed-variant"),
        "tertiary": colorVar("tertiary"),
        "on-tertiary": colorVar("on-tertiary"),
        "tertiary-container": colorVar("tertiary-container"),
        "on-tertiary-container": colorVar("on-tertiary-container"),
        "tertiary-dim": colorVar("tertiary-dim"),
        "tertiary-fixed": colorVar("tertiary-fixed"),
        "tertiary-fixed-dim": colorVar("tertiary-fixed-dim"),
        "on-tertiary-fixed": colorVar("on-tertiary-fixed"),
        "on-tertiary-fixed-variant": colorVar("on-tertiary-fixed-variant"),
        "error": colorVar("error"),
        "on-error": colorVar("on-error"),
        "error-container": colorVar("error-container"),
        "on-error-container": colorVar("on-error-container"),
        "error-dim": colorVar("error-dim"),
        "background": colorVar("background"),
        "on-background": colorVar("on-background"),
        "surface": colorVar("surface"),
        "on-surface": colorVar("on-surface"),
        "surface-variant": colorVar("surface-variant"),
        "on-surface-variant": colorVar("on-surface-variant"),
        "surface-dim": colorVar("surface-dim"),
        "surface-bright": colorVar("surface-bright"),
        "surface-container-lowest": colorVar("surface-container-lowest"),
        "surface-container-low": colorVar("surface-container-low"),
        "surface-container": colorVar("surface-container"),
        "surface-container-high": colorVar("surface-container-high"),
        "surface-container-highest": colorVar("surface-container-highest"),
        "surface-tint": colorVar("surface-tint"),
        "outline": colorVar("outline"),
        "outline-variant": colorVar("outline-variant"),
        "inverse-surface": colorVar("inverse-surface"),
        "inverse-on-surface": colorVar("inverse-on-surface"),
        "inverse-primary": colorVar("inverse-primary"),
      },
      fontFamily: {
        headline: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Public Sans", "sans-serif"],
        label: ["Public Sans", "sans-serif"],
      },
      borderRadius: {
        DEFAULT: "0.25rem",
        lg: "0.5rem",
        xl: "0.75rem",
        "2xl": "1rem",
        "3xl": "1.5rem",
        full: "9999px",
      },
    },
  },
  plugins: [],
};
