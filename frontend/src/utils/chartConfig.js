export const CHART_COLORS_LIGHT = [
  "#106a6a",
  "#7a5a00",
  "#954b00",
  "#005d5d",
  "#6b4e00",
  "#834100",
  "#9eeae9",
  "#ffdfa0",
  "#ffa35d",
  "#777b7c",
];

export const CHART_COLORS_DARK = [
  "#7ad4d3",
  "#e5c36c",
  "#ffb77c",
  "#5ec5c4",
  "#c8aa50",
  "#e69b5a",
  "#a0f0ef",
  "#ffd580",
  "#ffcba4",
  "#a8b5b4",
];

export function getChartColors(isDark) {
  return isDark ? CHART_COLORS_DARK : CHART_COLORS_LIGHT;
}

export function getTooltipStyles(isDark) {
  const tooltipTextColor = isDark ? "#e0e3e3" : "#2f3334";
  return {
    tooltipStyle: {
      borderRadius: "1rem",
      border: "none",
      boxShadow: isDark
        ? "0 4px 24px rgba(0,0,0,0.4)"
        : "0 4px 24px rgba(47,51,52,0.1)",
      fontFamily: "Public Sans",
      background: isDark ? "#282c2c" : "#fff",
      color: tooltipTextColor,
    },
    tooltipItemStyle: { color: tooltipTextColor },
    tooltipLabelStyle: { color: tooltipTextColor },
  };
}
