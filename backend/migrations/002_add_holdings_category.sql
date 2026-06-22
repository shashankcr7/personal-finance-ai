-- 002_add_holdings_category.sql
-- Adds an equity/debt/other classification to holdings, derived from
-- casparser's AMFI-enriched mutual fund type (confirmed available on
-- real CAS data). Needed for an accurate get_portfolio_allocation split.

alter table public.holdings
  add column category text not null default 'other'
  check (category in ('equity', 'debt', 'other'));
