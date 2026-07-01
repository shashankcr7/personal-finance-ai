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

import { apiGet, apiPostJson, ApiError } from "@/lib/api";
import { Modal } from "@/components/Modal";
import { formatDelta, formatINR } from "@/lib/money";
import type {
  Cashflow,
  Category,
  DashboardMonthly,
  Holding,
  Leak,
  LoanStatus,
  MonthlyTrends,
  PortfolioAllocation,
  Transaction,
} from "@/lib/types";

type View = "monthly" | "trends";

type ModalState =
  | { type: "income" }
  | { type: "expense" }
  | { type: "investments" }
  | { type: "networth" }
  | null;

function defaultMonthValue(): string {
  // Statements are always uploaded for the month that just ended, so default
  // to last month rather than the real current calendar month — otherwise
  // the Dashboard looks empty on every load until the picker is changed.
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 7);
}

type SortState<T extends string> = { column: T; direction: "asc" | "desc" } | null;

function toggleSort<T extends string>(current: SortState<T>, column: T): SortState<T> {
  if (!current || current.column !== column) return { column, direction: "asc" };
  if (current.direction === "asc") return { column, direction: "desc" };
  return null;
}

function compareForSort(a: string | number, b: string | number, direction: "asc" | "desc") {
  const result =
    typeof a === "number" && typeof b === "number" ? a - b : String(a).localeCompare(String(b));
  return direction === "asc" ? result : -result;
}

function SortableHeader<T extends string>({
  label,
  column,
  sort,
  onSort,
}: {
  label: string;
  column: T;
  sort: SortState<T>;
  onSort: (column: T) => void;
}) {
  const active = sort?.column === column;
  return (
    <button
      type="button"
      onClick={() => onSort(column)}
      className="flex items-center gap-1 text-xs font-medium text-gray-500 hover:text-gray-900"
    >
      {label} {active && (sort!.direction === "asc" ? "▲" : "▼")}
    </button>
  );
}

function KpiCard({
  label,
  value,
  deltaPct,
  sparkline,
  onClick,
}: {
  label: string;
  value: string;
  deltaPct: string | null;
  sparkline: (string | null)[];
  onClick?: () => void;
}) {
  const chartData = sparkline.map((v, i) => ({ i, v: v !== null ? Number(v) : null }));
  const isNegative = deltaPct !== null && deltaPct.startsWith("-");

  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={`rounded-lg border border-gray-200 bg-white p-4 ${
        onClick ? "cursor-pointer transition hover:border-gray-400 hover:shadow-sm" : ""
      }`}
    >
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
        {loan.percent_principal_paid}% paid · {loan.months_left} months left (recorded)
      </p>
      {loan.payoff_note ? (
        <p className="mt-2 text-xs text-amber-600">{loan.payoff_note}</p>
      ) : loan.projected_payoff_date ? (
        <p className="mt-2 text-xs text-gray-500">
          At your current EMI: payoff around {loan.projected_payoff_date} (~
          {loan.projected_months_remaining} months) — a projection, not a guarantee.
        </p>
      ) : null}
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

type TxnColumn = "date" | "description" | "category" | "amount";
const NEW_CATEGORY_SENTINEL = "__new__";

function IncomeExpenseModal({
  month,
  direction,
  title,
  total,
  onClose,
  onRecategorized,
}: {
  month: string;
  direction: "credit" | "debit";
  title: string;
  total: string;
  onClose: () => void;
  onRecategorized: () => void;
}) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortState<TxnColumn>>(null);
  const [filters, setFilters] = useState({ date: "", description: "", category: "", amount: "" });
  const [addingCategoryFor, setAddingCategoryFor] = useState<string | null>(null);
  const [newCategoryName, setNewCategoryName] = useState("");

  async function loadTransactions() {
    try {
      const data: Transaction[] = await apiGet("/transactions", { month: `${month}-01` });
      setTransactions(data.filter((t) => t.direction === direction));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not load transactions.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCategories() {
    try {
      const data: Category[] = await apiGet("/categories");
      setCategories(data);
    } catch {
      // category dropdown just stays empty; not worth a separate error banner
    }
  }

  useEffect(() => {
    loadTransactions();
    if (direction === "debit") loadCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month, direction]);

  async function handleCategoryChange(txnId: string, categoryId: string) {
    await apiPostJson(`/transactions/${txnId}/relabel`, { category_id: categoryId });
    await loadTransactions();
    onRecategorized();
  }

  async function handleAddCategory(txnId: string) {
    const name = newCategoryName.trim();
    if (!name) return;
    const { id } = await apiPostJson("/categories", { name });
    await apiPostJson(`/transactions/${txnId}/relabel`, { category_id: id });
    setAddingCategoryFor(null);
    setNewCategoryName("");
    await Promise.all([loadTransactions(), loadCategories()]);
    onRecategorized();
  }

  const filtered = transactions.filter((t) => {
    if (filters.date && !t.txn_date.includes(filters.date)) return false;
    if (
      filters.description &&
      !t.description.toLowerCase().includes(filters.description.toLowerCase())
    )
      return false;
    if (direction === "debit") {
      if (filters.category && t.category_id !== filters.category) return false;
    } else if (
      filters.category &&
      !t.category.toLowerCase().includes(filters.category.toLowerCase())
    ) {
      return false;
    }
    if (filters.amount && !formatINR(t.amount).includes(filters.amount)) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (!sort) return 0;
    const values: Record<TxnColumn, [string | number, string | number]> = {
      date: [a.txn_date, b.txn_date],
      description: [a.description, b.description],
      category: [a.category, b.category],
      amount: [Number(a.amount), Number(b.amount)],
    };
    const [av, bv] = values[sort.column];
    return compareForSort(av, bv, sort.direction);
  });

  const groups = new Map<string, Transaction[]>();
  for (const t of sorted) {
    const bank = t.bank.toUpperCase();
    if (!groups.has(bank)) groups.set(bank, []);
    groups.get(bank)!.push(t);
  }
  const bankNames = Array.from(groups.keys()).sort();

  function renderCategoryCell(t: Transaction) {
    if (addingCategoryFor === t.id) {
      return (
        <div className="flex flex-wrap items-center gap-1">
          <input
            autoFocus
            value={newCategoryName}
            onChange={(e) => setNewCategoryName(e.target.value)}
            placeholder="New category"
            className="w-24 rounded-md border border-gray-300 px-2 py-1 text-xs"
          />
          <button
            type="button"
            onClick={() => handleAddCategory(t.id)}
            className="text-xs font-medium text-gray-900 hover:underline"
          >
            Add
          </button>
          <button
            type="button"
            onClick={() => {
              setAddingCategoryFor(null);
              setNewCategoryName("");
            }}
            className="text-xs text-gray-400 hover:underline"
          >
            Cancel
          </button>
        </div>
      );
    }
    if (direction === "debit") {
      return (
        <select
          value={t.category_id ?? ""}
          onChange={(e) => {
            if (e.target.value === NEW_CATEGORY_SENTINEL) {
              setAddingCategoryFor(t.id);
            } else {
              handleCategoryChange(t.id, e.target.value);
            }
          }}
          className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
        >
          {!t.category_id && <option value="">Uncategorized</option>}
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
          <option value={NEW_CATEGORY_SENTINEL}>+ Add new category…</option>
        </select>
      );
    }
    return <span className="text-gray-700">{t.category}</span>;
  }

  const GRID_COLS = "grid-cols-[14%_36%_28%_22%]";

  return (
    <Modal title={title} onClose={onClose}>
      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && (
        <>
          {transactions.length === 0 ? (
            <p className="text-sm text-gray-500">No transactions for this month.</p>
          ) : (
            <div className="text-sm">
              <div className={`grid ${GRID_COLS} border-b border-gray-200 pb-1`}>
                <div className="px-3">
                  <SortableHeader label="Date" column="date" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
                </div>
                <div className="px-3">
                  <SortableHeader label="Description" column="description" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
                </div>
                <div className="px-3">
                  <SortableHeader label="Category" column="category" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
                </div>
                <div className="px-3 text-right">
                  <SortableHeader label="Amount" column="amount" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
                </div>
              </div>
              <div className={`grid ${GRID_COLS} pb-2 pt-2`}>
                <div className="px-3">
                  <input
                    value={filters.date}
                    onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
                    placeholder="Filter…"
                    className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                  />
                </div>
                <div className="px-3">
                  <input
                    value={filters.description}
                    onChange={(e) => setFilters((f) => ({ ...f, description: e.target.value }))}
                    placeholder="Filter…"
                    className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                  />
                </div>
                <div className="px-3">
                  {direction === "debit" ? (
                    <select
                      value={filters.category}
                      onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                    >
                      <option value="">All</option>
                      {categories.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      value={filters.category}
                      onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
                      placeholder="Filter…"
                      className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                    />
                  )}
                </div>
                <div className="px-3">
                  <input
                    value={filters.amount}
                    onChange={(e) => setFilters((f) => ({ ...f, amount: e.target.value }))}
                    placeholder="Filter…"
                    className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs text-right"
                  />
                </div>
              </div>

              {bankNames.map((bank) => (
                <details key={bank} open className="border-t border-gray-200">
                  <summary className="cursor-pointer select-none px-3 py-2 text-xs font-semibold text-gray-700">
                    {bank} ({groups.get(bank)!.length})
                  </summary>
                  <div>
                    {groups.get(bank)!.map((t) => (
                      <div
                        key={t.id}
                        className={`grid ${GRID_COLS} items-start border-t border-gray-100 py-2`}
                      >
                        <div className="px-3 text-gray-700">{t.txn_date}</div>
                        <div className="break-words whitespace-normal px-3 text-gray-700">
                          {t.description}
                        </div>
                        <div className="px-3">{renderCategoryCell(t)}</div>
                        <div className="px-3 text-right text-gray-900">{formatINR(t.amount)}</div>
                      </div>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          )}
          <div className="mt-3 flex justify-between border-t border-gray-200 px-3 pt-3 text-sm font-semibold text-gray-900">
            <span>Total ({title})</span>
            <span>{formatINR(total)}</span>
          </div>
        </>
      )}
    </Modal>
  );
}

type HoldingColumn = "name" | "asset_type" | "units" | "nav" | "market_value";

function InvestmentsModal({ onClose }: { onClose: () => void }) {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState<SortState<HoldingColumn>>(null);
  const [filters, setFilters] = useState({ name: "", asset_type: "" });

  useEffect(() => {
    apiGet("/holdings")
      .then(setHoldings)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load holdings."))
      .finally(() => setLoading(false));
  }, []);

  const filtered = holdings.filter((h) => {
    if (filters.name && !h.name.toLowerCase().includes(filters.name.toLowerCase())) return false;
    if (filters.asset_type && h.asset_type !== filters.asset_type) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (!sort) return 0;
    const values: Record<HoldingColumn, [string | number, string | number]> = {
      name: [a.name, b.name],
      asset_type: [a.asset_type, b.asset_type],
      units: [Number(a.units), Number(b.units)],
      nav: [Number(a.nav), Number(b.nav)],
      market_value: [Number(a.market_value), Number(b.market_value)],
    };
    const [av, bv] = values[sort.column];
    return compareForSort(av, bv, sort.direction);
  });

  return (
    <Modal title="Investments" onClose={onClose}>
      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && (
        <table className="w-full table-fixed text-left text-sm">
          <colgroup>
            <col className="w-[38%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[14%]" />
            <col className="w-[20%]" />
          </colgroup>
          <thead>
            <tr>
              <th className="px-3 pb-1">
                <SortableHeader label="Name" column="name" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
              </th>
              <th className="px-3 pb-1">
                <SortableHeader label="Type" column="asset_type" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
              </th>
              <th className="px-3 pb-1 text-right">
                <SortableHeader label="Units" column="units" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
              </th>
              <th className="px-3 pb-1 text-right">
                <SortableHeader label="NAV" column="nav" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
              </th>
              <th className="px-3 pb-1 text-right">
                <SortableHeader label="Value" column="market_value" sort={sort} onSort={(c) => setSort(toggleSort(sort, c))} />
              </th>
            </tr>
            <tr>
              <th className="px-3 pb-2">
                <input
                  value={filters.name}
                  onChange={(e) => setFilters((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Filter…"
                  className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                />
              </th>
              <th className="px-3 pb-2">
                <select
                  value={filters.asset_type}
                  onChange={(e) => setFilters((f) => ({ ...f, asset_type: e.target.value }))}
                  className="w-full rounded-md border border-gray-300 px-2 py-1 text-xs"
                >
                  <option value="">All</option>
                  <option value="stock">Stock</option>
                  <option value="mutual_fund">Mutual fund</option>
                </select>
              </th>
              <th className="px-3 pb-2" />
              <th className="px-3 pb-2" />
              <th className="px-3 pb-2" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((h, i) => (
              <tr key={`${h.isin}-${i}`} className="border-t border-gray-100 align-top">
                <td className="break-words whitespace-normal px-3 py-2 text-gray-700">
                  {h.name}
                </td>
                <td className="px-3 py-2 capitalize text-gray-600">
                  {h.asset_type.replace("_", " ")}
                </td>
                <td className="px-3 py-2 text-right text-gray-700">{h.units}</td>
                <td className="px-3 py-2 text-right text-gray-700">{h.nav}</td>
                <td className="px-3 py-2 text-right text-gray-900">{formatINR(h.market_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Modal>
  );
}

function NetWorthModal({
  summary,
  onClose,
}: {
  summary: DashboardMonthly;
  onClose: () => void;
}) {
  return (
    <Modal title="Net worth breakdown" onClose={onClose}>
      <ul className="space-y-2 text-sm text-gray-700">
        <li className="flex justify-between">
          <span>Equity holdings</span>
          <span>{formatINR(summary.portfolio_allocation.equity)}</span>
        </li>
        <li className="flex justify-between">
          <span>Debt holdings</span>
          <span>{formatINR(summary.portfolio_allocation.debt)}</span>
        </li>
        <li className="flex justify-between">
          <span>Other holdings</span>
          <span>{formatINR(summary.portfolio_allocation.other)}</span>
        </li>
        <li className="flex justify-between">
          <span>Cash (bank balances)</span>
          <span>{formatINR(summary.portfolio_allocation.cash)}</span>
        </li>
        {summary.loans.map((loan) => (
          <li key={loan.id} className="flex justify-between text-red-700">
            <span>Loan outstanding</span>
            <span>-{formatINR(loan.outstanding)}</span>
          </li>
        ))}
        <li className="flex justify-between border-t border-gray-200 pt-2 font-semibold text-gray-900">
          <span>Net worth</span>
          <span>{formatINR(summary.net_worth)}</span>
        </li>
      </ul>
    </Modal>
  );
}

export default function DashboardPage() {
  const [view, setView] = useState<View>("monthly");
  const [month, setMonth] = useState(defaultMonthValue());
  const [summary, setSummary] = useState<DashboardMonthly | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [modalState, setModalState] = useState<ModalState>(null);

  function loadSummary() {
    setLoading(true);
    setError(null);
    apiGet("/dashboard/monthly", { month: `${month}-01` })
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Could not load dashboard."))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month]);

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Dashboard</h1>
        <div className="flex items-center gap-3">
          {view === "monthly" && (
            <input
              type="month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            />
          )}
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
              onClick={() => setModalState({ type: "income" })}
            />
            <KpiCard
              label="Expenses"
              value={summary.cashflow.expense}
              deltaPct={summary.deltas.expense_pct}
              sparkline={summary.recent_trends.expense}
              onClick={() => setModalState({ type: "expense" })}
            />
            <KpiCard
              label="Investments"
              value={summary.portfolio_value}
              deltaPct={summary.deltas.portfolio_value_pct}
              sparkline={summary.recent_trends.portfolio_value}
              onClick={() => setModalState({ type: "investments" })}
            />
            <KpiCard
              label="Net worth"
              value={summary.net_worth}
              deltaPct={summary.deltas.net_worth_pct}
              sparkline={summary.recent_trends.net_worth}
              onClick={() => setModalState({ type: "networth" })}
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

      {modalState?.type === "income" && summary && (
        <IncomeExpenseModal
          month={month}
          direction="credit"
          title="Income"
          total={summary.cashflow.income}
          onClose={() => setModalState(null)}
          onRecategorized={loadSummary}
        />
      )}
      {modalState?.type === "expense" && summary && (
        <IncomeExpenseModal
          month={month}
          direction="debit"
          title="Expenses"
          total={summary.cashflow.expense}
          onClose={() => setModalState(null)}
          onRecategorized={loadSummary}
        />
      )}
      {modalState?.type === "investments" && (
        <InvestmentsModal onClose={() => setModalState(null)} />
      )}
      {modalState?.type === "networth" && summary && (
        <NetWorthModal summary={summary} onClose={() => setModalState(null)} />
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
