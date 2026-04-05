import { Layer, Rectangle } from "recharts";

const TOP_SANKEY_CATS = 8;

export function buildSankeyData(sankeyResp) {
  const { by_source, by_category, income_total, expenses_total, savings } = sankeyResp;
  if (!income_total || income_total === 0) return null;

  // Limit expense categories to top N; bucket the rest as "Other Expenses"
  const topCats = by_category.slice(0, TOP_SANKEY_CATS);
  const otherAmt = by_category.slice(TOP_SANKEY_CATS).reduce((s, c) => s + c.amount, 0);
  if (otherAmt > 0.01) topCats.push({ category: "Other Expenses", amount: otherAmt });

  // denominator for proportional distribution
  const denom = income_total >= expenses_total ? income_total : expenses_total;

  const sourceNodes = by_source.map((s) => ({ name: s.source }));
  const categoryNodes = topCats.map((c) => ({ name: c.category }));
  const savingsNode = savings > 0.01 ? [{ name: "Savings" }] : [];
  const nodes = [...sourceNodes, ...categoryNodes, ...savingsNode];

  const links = [];
  by_source.forEach((src, si) => {
    topCats.forEach((cat, ci) => {
      const value = parseFloat((src.amount * (cat.amount / denom)).toFixed(2));
      if (value > 0) links.push({ source: si, target: sourceNodes.length + ci, value });
    });
    if (savings > 0.01) {
      const value = parseFloat((src.amount * (savings / denom)).toFixed(2));
      if (value > 0) links.push({ source: si, target: nodes.length - 1, value });
    }
  });

  return { nodes, links, sourceCount: sourceNodes.length };
}

export function SankeyNode({ x, y, width, height, index, payload, sourceCount, isDark, chartColors }) {
  const isSource = index < sourceCount;
  const isSavings = payload.name === "Savings";
  const fill = isSavings
    ? (isDark ? "#5ec5c4" : "#106a6a")
    : isSource
      ? (isDark ? "#e5c36c" : "#7a5a00")
      : chartColors[index % chartColors.length];

  return (
    <Layer key={`node-${index}`}>
      <Rectangle x={x} y={y} width={width} height={height} fill={fill} fillOpacity={0.9} radius={4} />
      <text
        x={isSource ? x - 6 : x + width + 6}
        y={y + height / 2}
        textAnchor={isSource ? "end" : "start"}
        dominantBaseline="middle"
        fill={isDark ? "#e0e3e3" : "#2f3334"}
        fontSize={11}
        fontWeight={600}
      >
        {payload.name}
      </text>
    </Layer>
  );
}
