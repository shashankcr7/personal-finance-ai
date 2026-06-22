"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiGet, ApiError } from "@/lib/api";
import { formatDelta, formatINR } from "@/lib/money";
import type {
  Cashflow,
  DashboardMonthly,
  Leak,
  LoanStatus,
  MonthlyTrends,
  PortfolioAllocation,
} from "@/lib/types";

type View = "monthly" | "trends";

function currentMonthValue(): string {
  return new Date().toISOString().slice(0, 7);
}

function KpiCard({
  label,
  value,
  deltaPct,
  sparkline,
}: {
  label: string;
  value: string;
  deltaPct: string | null;
  sparkline: (string | null)[];
}) {
  const chartData = sparkline.map((v, i) => ({ i, v: v !== null ? Number(v) : null }));
  const isNegative = deltaPct !== null && deltaPct.startsWith("-");

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{formatINR(value)}</p>
      <div className="mt-2 flex items-center justify-between">
        <span
          className={`text-xs font-medium ${isNegative ? "text-red-600" : "text-green-600"}`}
        >
          {formatDelta(deltaPct)}
        </span>
        <div className="h-8 w-20">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke="#111827"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function LoanTrackerCard({ loan }: { loan: LoanStatus }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Loan outstanding</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{formatINR(loan.outstanding)}</p>
      <p className="mt-1 text-xs text-gray-500">
        {loan.rate}% · {formatINR(loan.emi)}/mo
      </p>
      <div className="mt-3 h-2 w-full rounded-full bg-gray-100">
        <div
          className="h-2 rounded-full bg-gray-900"
          style={{ width: `${Number(loan.percent_principal_paid)}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-gray-500">
        {loan.percent_principal_paid}% paid · {loan.months_left} months left
      </p>
    </div>
  );
}

function CashFlowCard({ cashflow }: { cashflow: Cashflow }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Cash flow</p>
      <div className="mt-2 flex items-end gap-6">
        <div>
          <p className="text-xs text-gray-500">Income</p>
          <p className="text-base font-semibold text-gray-900">{formatINR(cashflow.income)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Expense</p>
          <p className="text-base font-semibold text-gray-900">{formatINR(cashflow.expense)}</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-gray-700">
        Saved {formatINR(cashflow.saved)} ({cashflow.savings_rate}% of income)
      </p>
    </div>
  );
}

function SpendByCategoryCard({
  expenseByCategory,
}: {
  expenseByCategory: Record<string, string>;
}) {
  const entries = Object.entries(expenseByCategory).sort((a, b) => Number(b[1]) - Number(a[1]));
  const max = entries.length > 0 ? Number(entries[0][1]) : 0;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Spend by category</p>
      <div className="mt-3 space-y-2">
        {entries.length === 0 && <p className="text-sm text-gray-500">No spend this month.</p>}
        {entries.map(([category, amount]) => (
          <div key={category}>
            <div className="flex justify-between text-xs text-gray-600">
              <span>{category}</span>
              <span>{formatINR(amount)}</span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-gray-100">
              <div
                className="h-1.5 rounded-full bg-gray-700"
                style={{ width: `${max > 0 ? (Number(amount) / max) * 100 : 0}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const ALLOCATION_COLORS: Record<string, string> = {
  equity: "#111827",
  debt: "#6b7280",
  other: "#9ca3af",
  cash: "#d1d5db",
};

function PortfolioAllocationDonut({ allocation }: { allocation: PortfolioAllocation }) {
  const data = (["equity", "debt", "other", "cash"] as const)
    .map((key) => ({ key, name: key, value: Number(allocation[key]) }))
    .filter((entry) => entry.value > 0);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Portfolio allocation</p>
      <div className="mt-2 h-40">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={35} outerRadius={60}>
              {data.map((entry) => (
                <Cell key={entry.key} fill={ALLOCATION_COLORS[entry.key]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-2 space-y-1 text-xs text-gray-600">
        {(["equity", "debt", "other", "cash"] as const).map((key) => (
          <li key={key} className="flex justify-between capitalize">
            <span>{key}</span>
            <span>{formatINR(allocation[key])}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function LeakTile({ leak }: { leak: Leak }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">
        {leak.leak_type.replace(/_/g, " ")}
      </p>
      <p className="mt-1 text-lg font-semibold text-gray-900">{formatINR(leak.rupee_impact)}</p>
      <p className="mt-1 text-xs text-gray-600">{leak.detail}</p>
    </div>
  );
}

function CashFlowLineChart({ trends }: { trends: MonthlyTrends }) {
  const data = trends.months.map((month, i) => ({
    month,
    income: Number(trends.income[i]),
    expense: Number(trends.expense[i]),
    savings: Number(trends.savings[i]),
  }));

  return (
    <div className="h-72 rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Cash flow — income · expense · savings</p>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart data={data}>
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="income" stroke="#16a34a" dot={false} />
          <Line type="monotone" dataKey="expense" stroke="#dc2626" dot={false} />
          <Line type="monotone" dataKey="savings" stroke="#2563eb" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function PortfolioGrowthChart({ trends }: { trends: MonthlyTrends }) {
  const data = trends.months.map((month, i) => ({
    month,
    net_worth: trends.net_worth[i] !== null ? Number(trends.net_worth[i]) / 100000 : null,
    portfolio_value:
      trends.portfolio_value[i] !== null ? Number(trends.portfolio_value[i]) / 100000 : null,
  }));

  return (
    <div className="h-72 rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-xs text-gray-500">Net worth & portfolio value (₹ lakh)</p>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={data}>
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="net_worth" fill="#111827" />
          <Bar dataKey="portfolio_value" fill="#9ca3af" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function DashboardPage() {
  const [view, setView] = useState<View>("monthly");
  const [month, setMonth] = useState(currentMonthValue());
  const [summary, setSummary] = useState<DashboardMonthly | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    apiGet("/dashboard/monthly", { month: `${month}-01` })
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load dashboard."))
      .finally(() => setLoading(false));
  }, [month]);

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <div className="flex items-center gap-3">
          <div className="flex rounded-md border border-gray-300 text-sm">
            <button
              onClick={() => setView("monthly")}
              className={`px-3 py-1.5 ${view === "monthly" ? "bg-gray-900 text-white" : "text-gray-700"}`}
            >
              This month
            </button>
            <button
              onClick={() => setView("trends")}
              className={`px-3 py-1.5 ${view === "trends" ? "bg-gray-900 text-white" : "text-gray-700"}`}
            >
              All months
            </button>
          </div>
          {view === "monthly" && (
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            />
          )}
        </div>
      </div>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && summary && view === "monthly" && (
        <div className="space-y-6">
          {summary.cashflow.income === "0.00" && summary.cashflow.expense === "0.00" && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
              No transactions found for this month. Try a different month, or head to{" "}
              <strong>Upload</strong> to add a statement.
            </div>
          )}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <KpiCard
              label="Income"
              value={summary.cashflow.income}
              deltaPct={summary.deltas.income_pct}
              sparkline={summary.recent_trends.income}
            />
            <KpiCard
              label="Expenses"
              value={summary.cashflow.expense}
              deltaPct={summary.deltas.expense_pct}
              sparkline={summary.recent_trends.expense}
            />
            <KpiCard
              label="Investments"
              value={summary.portfolio_value}
              deltaPct={summary.deltas.portfolio_value_pct}
              sparkline={summary.recent_trends.portfolio_value}
            />
            <KpiCard
              label="Net worth"
              value={summary.net_worth}
              deltaPct={summary.deltas.net_worth_pct}
              sparkline={summary.recent_trends.net_worth}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {summary.loans.length > 0 && <LoanTrackerCard loan={summary.loans[0]} />}
            <CashFlowCard cashflow={summary.cashflow} />
            <PortfolioAllocationDonut allocation={summary.portfolio_allocation} />
          </div>

          <SpendByCategoryCard expenseByCategory={summary.expense_by_category} />

          <div>
            <h2 className="text-sm font-semibold text-gray-900">Where you&apos;re losing money</h2>
            {summary.leaks.length === 0 ? (
              <p className="mt-2 text-sm text-gray-500">No leaks detected this month.</p>
            ) : (
              <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-3">
                {summary.leaks.map((leak) => (
                  <LeakTile key={leak.leak_type} leak={leak} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {!loading && !error && summary && view === "trends" && (
        <TrendsView trends={summary.recent_trends} />
      )}
    </div>
  );
}

function TrendsView({ trends }: { trends: MonthlyTrends }) {
  const monthsWithActivity = trends.months.filter(
    (_, i) => trends.income[i] !== "0.00" || trends.expense[i] !== "0.00"
  ).length;

  if (monthsWithActivity < 2) {
    return (
      <p className="text-sm text-gray-500">
        Need a couple more months of data to show trends.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <CashFlowLineChart trends={trends} />
      <PortfolioGrowthChart trends={trends} />
    </div>
  );
}
