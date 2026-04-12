import { useState, useEffect } from "react";
import { useUsers } from "../ConfigContext";
import { useIncomeMode } from "../hooks/useIncomeMode";

const SECTIONS = [
  {
    id: "overview",
    icon: "home",
    title: "Overview",
    content: (mode, incomeEnabled) => [
      "Mosaic is a personal and collaborative expense-tracking app. It supports three modes: Personal (solo), Shared (split every expense with a partner), and Blended (mix of personal and shared expenses).",
      `You are currently in **${mode === "personal" ? "Personal" : mode === "blended" ? "Blended" : "Shared"}** mode. You can change this in Settings.`,
    ],
  },
  {
    id: "home",
    icon: "dashboard",
    title: "Home (Dashboard)",
    content: (mode, incomeEnabled) => {
      const lines = [
        "The Home page is your financial snapshot for the current month.",
      ];
      if (mode === "personal") {
        lines.push("**Your Expense This Month** — total amount you've spent this month across all categories.");
      } else {
        lines.push("**Current Balance** — shows how much one partner owes the other based on shared expenses and payments. When the balance is zero, you're settled up.");
        lines.push("**Your Expense This Month** — your personal share of all expenses: 50/50 splits count as half; Personal expenses count fully if you paid, zero otherwise; '100% you' splits count fully toward you regardless of who recorded it; '100% partner' splits count as zero for you.");
        lines.push("**Settle button** — quickly log a settlement payment so the balance returns to zero.");
      }
      if (incomeEnabled) {
        lines.push("**Income This Month** — total income logged this month, broken down by source (Salary, Freelance, Other).");
      }
      lines.push("**This Month's Spend by Category** — horizontal bar chart of your top 5 spending categories this month, sized relative to the largest category.");
      lines.push("**Recent Activity** — a table of your last 5 expenses showing description, category, date, amount, and (in shared/blended mode) who paid.");
      return lines;
    },
  },
  {
    id: "add",
    icon: "add_circle",
    title: (mode, incomeEnabled) => incomeEnabled ? "Add New (Expense & Income)" : "Add New (Expense)",
    content: (mode, incomeEnabled) => {
      const lines = [];
      if (incomeEnabled) {
        lines.push("This page has two tabs: **Expense** and **Income**. Toggle between them using the tab bar at the top.");
      }
      lines.push("### Adding an Expense");
      lines.push("**Amount** — the total cost of the expense (hero input at the top).");
      lines.push("**Date** — when the expense occurred. Dates are entered in your chosen format (configurable in Settings). A calendar picker icon is available for convenience. Future dates are not allowed.");
      lines.push("**Description** — what the expense was for. As you type, the app suggests matching descriptions from your history (fuzzy search). Selecting a suggestion auto-fills the category.");
      lines.push("**Auto-suggested category** — when you type a description, Mosaic automatically suggests a category based on your past expenses. A sparkle indicator appears when a category has been auto-suggested.");
      lines.push("**Category** — choose from predefined categories (Groceries, Rent, Utilities, Dining, Transportation, Entertainment, Healthcare, Shopping, Travel, Payment, Gas, Car Insurance, Car Maintenance, Home Care, Pet Care, Pet Insurance, Vet, Gift, Subscription, Parking, Tenant Insurance, Reimbursement, Other) or create a custom category with \"+ New Category\".");
      lines.push("**Note on amounts:** Zero amounts are not allowed. Negative amounts are only permitted for the Reimbursement category (used to record money received back). Future dates are not allowed.");
      if (mode !== "personal") {
        lines.push("**Who Paid** — select which partner paid for the expense.");
        lines.push("**Split Method** — choose how to split the expense:");
        lines.push("  - **50/50** — split equally between both partners.");
        lines.push("  - **100% (Other Owes)** — the other person owes the full amount.");
        lines.push("  - **Personal** — only the payer is responsible; it does not affect the shared balance.");
      }
      if (incomeEnabled) {
        lines.push("### Adding Income");
        lines.push("**Amount Received** — how much income you received.");
        lines.push("**Date** — when you received the income.");
        lines.push("**Source** — choose from Salary/Wages, Freelance/Side Income, or Other.");
        lines.push("**Notes** — optional free-text notes (e.g. \"March salary\").");
      }
      return lines;
    },
  },
  {
    id: "analytics",
    icon: "bar_chart",
    title: "Analytics",
    content: (mode, incomeEnabled) => {
      const lines = [
        "The Analytics page visualizes your spending data with interactive charts.",
        "### Date Range",
        "Use the preset buttons (1M, 3M, 6M, YTD, 1Y, All) or set a custom date range to filter all charts.",
      ];
      if (incomeEnabled) {
        lines.push("### Income Flow (Sankey Chart)");
        lines.push("A Sankey diagram showing where your money comes from (income sources on the left) and where it goes (expense categories on the right). If you have positive savings, a \"Savings\" node appears. Up to 8 expense categories are shown; the rest are bucketed as \"Other Expenses\".");
      }
      lines.push("### Your Expense Summary");
      lines.push("A large card showing your total personal share of expenses for the selected period.");
      if (mode !== "personal") {
        lines.push("Also shows the total shared spend and partner avatars.");
      }
      lines.push("### Category Distribution (Pie Chart)");
      lines.push("A donut chart breaking down spending by category (top 7 + Others). **Click any slice** to drill down into that category and see a horizontal bar chart of top expenses by description within it.");
      lines.push("### Spending Velocity (Line Chart)");
      lines.push("Monthly spending trend as a line chart. Shows total spend and expense count per month. When you've drilled into a category, this chart shows that category's monthly trend instead. **Click any data point** to jump to the History page filtered to that month.");
      if (mode !== "personal") {
        lines.push("### Payer Breakdown");
        lines.push("Shows how much each partner has paid and their percentage of total spend.");
      }
      if (mode === "blended") {
        lines.push("### Personal vs Shared");
        lines.push("Breaks down your spending into Personal and Shared portions with percentage bars.");
      }
      lines.push("### Largest Outlays");
      lines.push("A table of your biggest expenses in the selected period, with description, category, payer, date, and amount.");
      return lines;
    },
  },
  {
    id: "calendar",
    icon: "calendar_month",
    title: "Calendar",
    content: (mode, incomeEnabled) => {
      const lines = [
        "A monthly calendar view of your daily spending.",
        "### Navigation",
        "Use the left/right arrows to move between months. Click the month/year label to open a month-year picker where you can jump to any month from 2000\u20132099.",
        "### Monthly Summary",
        "At the top, a card shows your total personal expense for the displayed month, the number of expenses, and (in shared/blended mode) the total shared spend.",
        "### Calendar Grid",
        "Each day cell shows your personal share of expenses for that day. The background intensity uses a logarithmic heat-map scale \u2014 darker cells indicate higher spending relative to the month's range. Today is highlighted with a ring.",
      ];
      if (incomeEnabled) {
        lines.push("Days with income are marked with a **+** badge and a green amount below the expense amount.");
      }
      lines.push("**Click any day** to jump to the History page filtered to that specific date.");
      lines.push("Payment-category expenses are excluded from the calendar totals. Reimbursements are included (their negative amounts reduce the day's total).");
      return lines;
    },
  },
  {
    id: "insights",
    icon: "lightbulb",
    title: "Insights",
    content: (mode, incomeEnabled) => {
      const lines = [
        "The Insights page provides automated, AI-style analysis of your spending patterns.",
        "### Alert Banners",
        "**Recurring payment alerts** — flags when a recurring expense (e.g. a subscription) has changed significantly from its historical average, showing the old vs. new amount and percentage change.",
        "**Category trend alerts** — flags categories where this month's spending is significantly above or below the 3-month average.",
        "### Forecast",
        "Predicts next month's total expense, broken down into recurring (predictable) and variable portions. Shows a per-category comparison of forecast vs. last month in a horizontal bar chart. Also shows the percentage change from the previous month. Requires at least 1 month of history.",
        "### Unusual Expenses (Anomalies)",
        "Cards highlighting individual expenses that are statistically unusual \u2014 either much higher or lower than the category average. Shows the expense description, amount, category mean, and date.",
        "### Recurring Expenses",
        "A table of detected recurring expenses, showing description, category, detected frequency (Weekly, Biweekly, Monthly, Quarterly, Annual), average amount, last amount, and total occurrences. Sorted by occurrence count.",
        "### Weekend vs Weekday Spending",
        "Compares your weekday and weekend spending per transaction, total counts, and weekend share percentage. A per-category bar chart shows the weekday/weekend breakdown for the top 8 categories.",
      ];
      if (mode !== "personal") {
        lines.push("In shared/blended mode, separate panels show \"Your Expense\" and \"Shared Expense\" breakdowns.");
      }
      lines.push("### Top Growing Categories");
      lines.push("Lists categories with the highest month-over-month growth rate, showing the last 3 months of data. Requires at least 2 months of data.");
      if (incomeEnabled) {
        lines.push("### Income Insights (when income tracking is enabled)");
        lines.push("**Savings Rate** — current month's savings rate percentage, with income, expenses, and net savings breakdown. Color-coded: green for positive savings, red for negative.");
        lines.push("**Income by Source** — horizontal bar chart showing this month's income by source.");
        lines.push("**Income vs Expenses** — a composed chart with bars for income and expenses per month, plus a line for surplus/deficit.");
        lines.push("**Savings Rate Trend** — a line chart tracking your savings rate percentage over time.");
      }
      return lines;
    },
  },
  {
    id: "history",
    icon: "receipt_long",
    title: "Expenses (History)",
    content: (mode, incomeEnabled) => {
      const lines = [
        "A detailed, filterable list of all your expenses.",
        "### Search",
        "Type in the search bar and press Enter to filter expenses by description text.",
        "### Filters",
        "**Category** — filter by any expense category.",
      ];
      if (mode !== "personal") {
        lines.push("**Paid By** — filter by which partner paid.");
      }
      if (mode === "blended") {
        lines.push("**Type** — filter by Personal or Shared expenses.");
      }
      lines.push("**Amount** — sort by amount (High to Low, or Low to High).");
      lines.push("### Expense Table");
      lines.push("Each row shows: date, description with category icon and badge, amount, and (in shared/blended mode) who paid and the split type (Split, Personal, or Separate).");
      lines.push("**Edit** — click the pencil icon to edit any expense's details.");
      lines.push("**Delete** — click the trash icon to permanently delete an expense (with confirmation dialog).");
      lines.push("Up to 100 expenses are shown at a time.");
      lines.push("### Drill-down from Analytics");
      lines.push("When you click a data point in the Spending Velocity chart on Analytics, you land here with the month (and optionally category) pre-filtered. A filter pill at the top shows the active filter; click the \u00D7 to clear it.");
      lines.push("### Export");
      lines.push("Click **Export** to download your expenses as a spreadsheet file. The export respects your current search and filter selections.");
      lines.push("### Clean Up (Merge Descriptions)");
      lines.push("Click **Clean Up** to open a modal that helps you standardize similar expense descriptions:");
      lines.push("  - **Suggestions tab** — the app uses embedding-based similarity analysis to find groups of similar descriptions within each category. For each group, choose a target name and click Accept to rename all variants, or Reject to permanently dismiss that suggestion.");
      lines.push("  - **Custom Merge tab** — manually pick a category, enter a target description, and add source descriptions to rename.");
      lines.push("  - **Dismissed tab** — review and restore previously rejected merge suggestions.");
      return lines;
    },
  },
  {
    id: "settings",
    icon: "settings",
    title: "Settings",
    content: (mode, incomeEnabled) => {
      const lines = [
        "Configure how you use Mosaic.",
        "### Profile Picture",
        "Upload a custom avatar photo. Your display name is shown alongside it.",
      ];
      if (mode === "personal" || mode === "blended") {
        lines.push("### Income Tracking");
        lines.push("Toggle income tracking on or off. When enabled, you can log income entries and see income-related visualizations in the Home dashboard, Analytics (Sankey chart), Calendar (income badges), and Insights (savings rate, income vs expenses). Available in Personal and Blended modes only.");
      }
      lines.push("### App Mode");
      lines.push("Switch between three modes:");
      lines.push("  - **Personal** — track your own expenses only.");
      lines.push("  - **Shared** — every expense is split between two partners.");
      lines.push("  - **Blended** — mix of personal and shared expenses.");
      lines.push("Shared and Blended modes require a second registered user. A banner appears when a second user has registered to prompt you to switch.");
      lines.push("### Date Format");
      lines.push("Choose how dates are displayed and entered throughout the app. Options: DD/MM/YYYY, MM/DD/YYYY, YYYY/MM/DD, YYYY/DD/MM. This setting is saved per-user on the server.");
      lines.push("### Stay Signed In");
      lines.push("Toggle to stay logged in for up to a year instead of the default 8-hour session.");
      lines.push("### Security");
      lines.push("**Change Password** — update your password by entering your current password and a new one (minimum 6 characters).");
      lines.push("### Danger Zone");
      lines.push("**Delete Account** — permanently delete your account. You must enter your password. Choose to either anonymize your data (expenses labeled \"Deleted User\") or delete all your data entirely.");
      return lines;
    },
  },
  {
    id: "navbar",
    icon: "menu",
    title: "Navigation & Toolbar",
    content: () => [
      "### Top Navigation Bar",
      "**Logo & Mode Badge** — the Mosaic logo links to Home. The badge next to it shows your current mode (Personal, Shared, or Blended).",
      "**Desktop Nav Links** — Home, Add New, Analytics, Calendar, Insights, Expenses.",
      "**Helper Icon** — this guide you're reading now.",
      "**Settings Icon** — navigate to the Settings page.",
      "**User Avatar & Name** — your profile picture and display name (visible on larger screens).",
      "**Currency Selector** — switch the display currency symbol (USD, EUR, GBP, CAD, AUD, INR, JPY, CNY, CHF, SGD). This is display-only and does not convert amounts.",
      "**Dark/Light Mode Toggle** — switch between dark and light themes. Your preference is saved in local storage.",
      "**Logout Button** — sign out of your account.",
      "### Mobile Bottom Navigation",
      "On mobile devices, a bottom nav bar provides quick access to: Home, Add New, Calendar, Insights, and Expenses.",
    ],
  },
  {
    id: "auth",
    icon: "lock",
    title: "Account & Authentication",
    content: () => [
      "### Sign In",
      "Log in with your username and password.",
      "### Create Account",
      "Register a new account with a display name, username, password, and security question/answer. A maximum of 2 accounts can be created. After the first account is created, the second user can register.",
      "### Forgot Password",
      "Reset your password by entering your username, answering your security question, and setting a new password.",
    ],
  },
];

function renderLine(line, i) {
  if (line.startsWith("### ")) {
    return (
      <h4
        key={i}
        className="font-headline text-sm font-bold text-on-surface mt-4 mb-1"
      >
        {line.slice(4)}
      </h4>
    );
  }

  // Render bold segments marked with **...**
  const parts = line.split(/(\*\*[^*]+\*\*)/g);
  return (
    <p key={i} className="text-sm text-on-surface-variant leading-relaxed">
      {parts.map((part, j) =>
        part.startsWith("**") && part.endsWith("**") ? (
          <span key={j} className="font-bold text-on-surface">
            {part.slice(2, -2)}
          </span>
        ) : (
          part
        ),
      )}
    </p>
  );
}

export default function HelpModal({ onClose }) {
  const { mode } = useUsers();
  const { incomeEnabled } = useIncomeMode();
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const section = SECTIONS.find((s) => s.id === activeSection) || SECTIONS[0];
  const lines = section.content(mode, incomeEnabled);
  const resolveTitle = (s) => typeof s.title === "function" ? s.title(mode, incomeEnabled) : s.title;

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface-container-lowest rounded-[2rem] shadow-xl w-full max-w-3xl max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 pb-0 sm:p-8 sm:pb-0">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="font-headline text-2xl font-extrabold text-on-surface mb-1">
                App Guide
              </h2>
              <p className="text-on-surface-variant text-sm">
                Everything you need to know about Mosaic.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-surface-container-high transition-colors text-on-surface-variant"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          {/* Sidebar nav */}
          <nav className="hidden sm:flex flex-col w-52 shrink-0 border-r border-outline-variant/10 overflow-y-auto py-2 px-2">
            {SECTIONS.map((s) => {
              const isActive = activeSection === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setActiveSection(s.id)}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-xl text-left text-sm transition-colors mb-0.5 ${
                    isActive
                      ? "bg-primary-container/30 text-primary font-bold"
                      : "text-on-surface-variant hover:bg-surface-container-high font-medium"
                  }`}
                >
                  <span
                    className="material-symbols-outlined text-[18px]"
                    style={
                      isActive
                        ? { fontVariationSettings: "'FILL' 1" }
                        : undefined
                    }
                  >
                    {s.icon}
                  </span>
                  {resolveTitle(s)}
                </button>
              );
            })}
          </nav>

          {/* Mobile section selector */}
          <div className="sm:hidden w-full flex flex-col overflow-hidden">
            <div className="px-4 pt-2 pb-3 border-b border-outline-variant/10 overflow-x-auto">
              <div className="flex gap-1.5">
                {SECTIONS.map((s) => {
                  const isActive = activeSection === s.id;
                  return (
                    <button
                      key={s.id}
                      onClick={() => setActiveSection(s.id)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-colors ${
                        isActive
                          ? "bg-primary text-on-primary font-bold"
                          : "bg-surface-container-high text-on-surface-variant font-medium"
                      }`}
                    >
                      <span className="material-symbols-outlined text-[14px]">
                        {s.icon}
                      </span>
                      {resolveTitle(s)}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Mobile content */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
              <div className="flex items-center gap-2 mb-3">
                <span
                  className="material-symbols-outlined text-primary"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  {section.icon}
                </span>
                <h3 className="font-headline text-lg font-bold text-on-surface">
                  {resolveTitle(section)}
                </h3>
              </div>
              {lines.map((line, i) => renderLine(line, i))}
            </div>
          </div>

          {/* Desktop content */}
          <div className="hidden sm:flex flex-col flex-1 overflow-hidden">
            <div className="flex-1 overflow-y-auto px-8 py-6 space-y-2">
              <div className="flex items-center gap-2 mb-4">
                <span
                  className="material-symbols-outlined text-primary"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  {section.icon}
                </span>
                <h3 className="font-headline text-lg font-bold text-on-surface">
                  {resolveTitle(section)}
                </h3>
              </div>
              {lines.map((line, i) => renderLine(line, i))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 sm:p-8 pt-4 border-t border-outline-variant/10">
          <button
            onClick={onClose}
            className="w-full bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
