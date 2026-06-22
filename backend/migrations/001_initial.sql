-- 001_initial.sql
-- Initial schema: users, accounts, statement_uploads, categories,
-- category_rules, transactions, holdings, loans, goals,
-- monthly_snapshots, chat_messages.
-- Every table has RLS enabled with a policy scoped to auth.uid().

create extension if not exists pgcrypto;

-- ──────────────────────────────────────────────────────────────────
-- users — profile row 1:1 with Supabase Auth. id is NOT auto-generated:
-- it must equal the Auth UID so every other table's policy can compare
-- user_id = auth.uid() directly, with no join through this table.
-- ──────────────────────────────────────────────────────────────────
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  display_name text,
  created_at timestamptz not null default now()
);

alter table public.users enable row level security;

create policy "users_self_access" on public.users
  for all
  using (id = auth.uid())
  with check (id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- accounts — one row per bank/demat/mutual_fund/loan account a user holds.
-- ──────────────────────────────────────────────────────────────────
create table public.accounts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  type text not null check (type in ('bank', 'demat', 'mutual_fund', 'loan')),
  institution_name text not null,
  nickname text,
  created_at timestamptz not null default now()
);

create index accounts_user_id_idx on public.accounts (user_id);

alter table public.accounts enable row level security;

create policy "accounts_owner_access" on public.accounts
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- statement_uploads — audit trail of each upload (CAS PDF / bank CSV).
-- Only metadata is stored; the raw file itself is parsed then discarded.
-- ──────────────────────────────────────────────────────────────────
create table public.statement_uploads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  account_id uuid references public.accounts(id) on delete set null,
  source_type text not null check (source_type in ('cas', 'bank_csv', 'bank_xlsx')),
  original_filename text,
  status text not null default 'pending' check (status in ('pending', 'parsing', 'success', 'error')),
  error_message text,
  as_of_date date,
  created_at timestamptz not null default now()
);

create index statement_uploads_user_id_idx on public.statement_uploads (user_id);
create index statement_uploads_account_id_idx on public.statement_uploads (account_id);

alter table public.statement_uploads enable row level security;

create policy "statement_uploads_owner_access" on public.statement_uploads
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- categories — per-user taxonomy, self-referencing for parent/child hierarchy.
-- ──────────────────────────────────────────────────────────────────
create table public.categories (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  parent_id uuid references public.categories(id) on delete set null,
  created_at timestamptz not null default now()
);

create index categories_user_id_idx on public.categories (user_id);
create index categories_parent_id_idx on public.categories (parent_id);

alter table public.categories enable row level security;

create policy "categories_owner_access" on public.categories
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- category_rules — merchant_normalized → category, one rule per merchant
-- per user. Relabeling a transaction upserts here (ON CONFLICT on the
-- unique constraint below) and the rule applies to all past/future matches.
-- ──────────────────────────────────────────────────────────────────
create table public.category_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  merchant_normalized text not null,
  category_id uuid not null references public.categories(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, merchant_normalized)
);

create index category_rules_user_id_idx on public.category_rules (user_id);
create index category_rules_category_id_idx on public.category_rules (category_id);

alter table public.category_rules enable row level security;

create policy "category_rules_owner_access" on public.category_rules
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- transactions — normalized bank transactions. Dedupe constraint matches
-- BUILD_SPEC 1.2 exactly so re-uploading an overlapping statement is a no-op.
-- ──────────────────────────────────────────────────────────────────
create table public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  txn_date date not null,
  amount numeric(14, 2) not null,
  direction text not null check (direction in ('debit', 'credit')),
  description text not null,
  balance_after numeric(14, 2),
  merchant_normalized text,
  ai_category_id uuid references public.categories(id) on delete set null,
  final_category_id uuid references public.categories(id) on delete set null,
  created_at timestamptz not null default now(),
  unique (account_id, txn_date, amount, description)
);

create index transactions_user_id_idx on public.transactions (user_id);
create index transactions_account_id_idx on public.transactions (account_id);
create index transactions_txn_date_idx on public.transactions (txn_date);

alter table public.transactions enable row level security;

create policy "transactions_owner_access" on public.transactions
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- holdings — CAS-parsed stock/mutual_fund positions. units/nav keep extra
-- decimal precision since CAS reports fractional units and 4-decimal NAVs;
-- market_value/cost_value are the already-computed rupee totals.
-- ──────────────────────────────────────────────────────────────────
create table public.holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  asset_type text not null check (asset_type in ('stock', 'mutual_fund')),
  isin text not null,
  name text not null,
  units numeric(18, 4) not null,
  nav numeric(14, 4) not null,
  market_value numeric(14, 2) not null,
  cost_value numeric(14, 2),
  as_of_date date not null,
  created_at timestamptz not null default now()
);

create index holdings_user_id_idx on public.holdings (user_id);
create index holdings_account_id_idx on public.holdings (account_id);

alter table public.holdings enable row level security;

create policy "holdings_owner_access" on public.holdings
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- loans — manually entered loan tracker. original_principal is required
-- to compute % principal paid.
-- ──────────────────────────────────────────────────────────────────
create table public.loans (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  account_id uuid not null references public.accounts(id) on delete cascade,
  original_principal numeric(14, 2) not null,
  principal_outstanding numeric(14, 2) not null,
  interest_rate numeric(5, 2) not null,
  emi_amount numeric(14, 2) not null,
  tenure_months_left integer not null,
  as_of_date date not null,
  created_at timestamptz not null default now()
);

create index loans_user_id_idx on public.loans (user_id);
create index loans_account_id_idx on public.loans (account_id);

alter table public.loans enable row level security;

create policy "loans_owner_access" on public.loans
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- goals — user-defined goals with their own visible, editable return
-- assumption (never the LLM's assumption).
-- ──────────────────────────────────────────────────────────────────
create table public.goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  name text not null,
  target_amount numeric(14, 2) not null,
  target_date date not null,
  priority text,
  assumed_return numeric(5, 2) not null,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index goals_user_id_idx on public.goals (user_id);

alter table public.goals enable row level security;

create policy "goals_owner_access" on public.goals
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- monthly_snapshots — net worth / portfolio value / total invested,
-- written once per user per month at each CAS upload (BUILD_SPEC §5).
-- ──────────────────────────────────────────────────────────────────
create table public.monthly_snapshots (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  month date not null,
  net_worth numeric(14, 2) not null,
  portfolio_value numeric(14, 2) not null,
  total_invested numeric(14, 2) not null,
  created_at timestamptz not null default now(),
  unique (user_id, month)
);

create index monthly_snapshots_user_id_idx on public.monthly_snapshots (user_id);

alter table public.monthly_snapshots enable row level security;

create policy "monthly_snapshots_owner_access" on public.monthly_snapshots
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- ──────────────────────────────────────────────────────────────────
-- chat_messages — agent conversation turns.
-- ──────────────────────────────────────────────────────────────────
create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

create index chat_messages_user_id_idx on public.chat_messages (user_id);

alter table public.chat_messages enable row level security;

create policy "chat_messages_owner_access" on public.chat_messages
  for all
  using (user_id = auth.uid())
  with check (user_id = auth.uid());
