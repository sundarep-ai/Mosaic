import { Link } from "react-router-dom";
import AlertBanners from "./AlertBanners";
import { useCurrency } from "../../CurrencyContext";
import { selectTopAlerts, getForecastLine } from "../../utils/insightsPreview";

export default function InsightsPreview({ recurring_alerts = [], category_trend_alerts = [], forecast, mode }) {
  const { fmt } = useCurrency();
  const { recurring, trend } = selectTopAlerts(recurring_alerts, category_trend_alerts);
  const forecastLine = getForecastLine(forecast, fmt);
  const hasAlerts = recurring.length > 0 || trend.length > 0;

  if (!hasAlerts && !forecastLine) return null;

  return (
    <section className="bg-surface-container-lowest rounded-[2rem] p-6 md:p-8 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-headline text-lg font-bold flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">auto_awesome</span>
          Insights
        </h3>
        <Link
          to="/insights"
          className="text-primary font-bold text-sm flex items-center gap-1 hover:underline"
        >
          See all insights
          <span className="material-symbols-outlined text-[18px]">chevron_right</span>
        </Link>
      </div>
      {hasAlerts && (
        <AlertBanners recurring_alerts={recurring} category_trend_alerts={trend} mode={mode} />
      )}
      {forecastLine && (
        <p className="text-sm text-on-surface-variant font-medium">{forecastLine}</p>
      )}
    </section>
  );
}
