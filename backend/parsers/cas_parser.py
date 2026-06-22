from datetime import datetime
from decimal import Decimal

from casparser import read_cas_pdf
from casparser.exceptions import CASParseError
from casparser.types import NSDLCASData

# Below this, a gap between an account's reported balance and its parsed holdings
# is just rounding noise across multiple schemes, not unaccounted money.
RECONCILIATION_TOLERANCE = Decimal("1.00")


def parse_cas(file_obj, password: str) -> list[dict]:
    try:
        data = read_cas_pdf(file_obj, password)
    finally:
        file_obj.close()

    if not isinstance(data, NSDLCASData):
        raise CASParseError(
            "Expected an NSDL/CDSL depository CAS (stocks + mutual funds); "
            "got a different statement type."
        )

    return _holdings_from_nsdl_data(data)


def _mf_category(mf_type: str | None) -> str:
    if mf_type and mf_type.strip().upper() == "EQUITY":
        return "equity"
    if mf_type and mf_type.strip().upper() == "DEBT":
        return "debt"
    return "other"


def _holdings_from_nsdl_data(data: NSDLCASData) -> list[dict]:
    as_of_date = datetime.strptime(data.statement_period.to, "%d-%b-%Y").date()

    holdings = []
    for account in data.accounts:
        accounted_value = Decimal("0")

        for equity in account.equities:
            # A real holding's price is never genuinely zero — some NSDL CAS PDF
            # folio rows come back from casparser with nav/price=0 and a bogus
            # near-zero value alongside it. Omitting a position beats showing a
            # market value we know is wrong.
            if equity.price <= 0:
                continue
            holdings.append(
                {
                    "asset_type": "stock",
                    "isin": equity.isin,
                    "name": equity.name,
                    "units": equity.num_shares,
                    "nav": equity.price,
                    "market_value": equity.value,
                    "cost_value": None,
                    "as_of_date": as_of_date,
                    "category": "equity",
                }
            )
            accounted_value += equity.value
        for mf in account.mutual_funds:
            if mf.nav <= 0:
                continue
            holdings.append(
                {
                    "asset_type": "mutual_fund",
                    "isin": mf.isin,
                    "name": mf.name,
                    "units": mf.balance,
                    "nav": mf.nav,
                    "market_value": mf.value,
                    "cost_value": mf.total_cost,
                    "as_of_date": as_of_date,
                    "category": _mf_category(mf.type),
                }
            )
            accounted_value += mf.value

        # NSDL reports account.balance as the depository/folio group's own total,
        # independent of casparser's per-scheme breakdown. When schemes we had to
        # skip (or simply don't itemize) leave real money unaccounted for, surface
        # it as one reconciliation line rather than silently dropping it.
        gap = account.balance - accounted_value
        if gap > RECONCILIATION_TOLERANCE:
            holdings.append(
                {
                    "asset_type": "mutual_fund",
                    "isin": f"UNALLOCATED-{account.name}",
                    "name": (
                        f"Unidentified holdings in {account.name} "
                        "(CAS total not fully broken down by scheme)"
                    ),
                    "units": Decimal("0"),
                    "nav": Decimal("0"),
                    "market_value": gap.quantize(Decimal("0.01")),
                    "cost_value": None,
                    "as_of_date": as_of_date,
                    "category": "other",
                }
            )
    return holdings
