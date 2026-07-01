// Every money/percentage value from the API is a decimal string (e.g. "15000.00"),
// never a number — the backend never sends a value that's round-tripped through float,
// and the frontend must only format/display these, never compute with them.

export type Cashflow = {
  income: string;
  expense: string;
  saved: string;
  savings_rate: string;
};

export type PortfolioAllocation = {
  equity: string;
  debt: string;
  other: string;
  cash: string;
};

export type LoanStatus = {
  id: string;
  outstanding: string;
  percent_principal_paid: string;
  rate: string;
  emi: string;
  months_left: number;
  projected_months_remaining: number | null;
  projected_payoff_date: string | null;
  payoff_note: string | null;
};

export type GoalProgress = {
  id: string;
  name: string;
  priority: string | null;
  notes: string | null;
  current_value: string;
  projected_value: string;
  percent_funded: string;
  on_track: boolean;
  assumed_return: string;
  target_amount: string;
  target_date: string;
  is_projection: boolean;
};

export type Leak = {
  leak_type: string;
  rupee_impact: string;
  detail: string;
};

export type Deltas = {
  income_pct: string | null;
  expense_pct: string | null;
  net_worth_pct: string | null;
  portfolio_value_pct: string | null;
};

export type MonthlyTrends = {
  months: string[];
  income: string[];
  expense: string[];
  savings: string[];
  net_worth: (string | null)[];
  portfolio_value: (string | null)[];
};

export type DashboardMonthly = {
  cashflow: Cashflow;
  expense_by_category: Record<string, string>;
  net_worth: string;
  portfolio_value: string;
  portfolio_allocation: PortfolioAllocation;
  loans: LoanStatus[];
  goals: GoalProgress[];
  leaks: Leak[];
  recent_trends: MonthlyTrends;
  deltas: Deltas;
};

export type RecentUpload = {
  id: string;
  source_type: "cas" | "bank_csv" | "bank_xlsx";
  original_filename: string | null;
  status: "pending" | "parsing" | "success" | "error";
  error_message: string | null;
  as_of_date: string | null;
  created_at: string;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type Transaction = {
  id: string;
  txn_date: string;
  amount: string;
  direction: "credit" | "debit";
  description: string;
  merchant_normalized: string | null;
  category: string;
  category_id: string | null;
  bank: string;
};

export type Category = {
  id: string;
  name: string;
  parent_id: string | null;
};

export type Holding = {
  asset_type: "stock" | "mutual_fund";
  isin: string;
  name: string;
  units: string;
  nav: string;
  market_value: string;
  cost_value: string | null;
  as_of_date: string;
  category: "equity" | "debt" | "other";
};
