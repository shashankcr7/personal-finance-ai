import pytest

from parsers.merchant_normalizer import normalize_merchant

NORMALIZER_CORPUS = [
    (
        "UPI/SWIGGY-1234/998877665544/PAYMENT FROM PHONEPE",
        "SWIGGY PAYMENT FROM PHONEPE",
    ),
    ("UPI/Zomato Online/zomato@ybl/UPI", "ZOMATO ONLINE UPI"),
    ("IMPS/412233445566/JOHN TRAVEL AGENCY/AXIS", "JOHN TRAVEL AGENCY AXIS"),
    (
        "NEFT/123456789012/ACME CORP SALARY/HDFC0001234",
        "ACME CORP SALARY HDFC0001234",
    ),
    ("ACH/D/HDFCMF SIP/30-06-2024", "D HDFCMF SIP"),
    ("POS/AMAZON RETAIL/12-Jun-2024/45678", "POS AMAZON RETAIL"),
    ("UPI/Big Bazaar-99/bigbazaar@icici/Payment", "BIG BAZAAR PAYMENT"),
    ("IMPS/P2A/998877/Rent to Landlord/01/07/2024", "P2A RENT TO LANDLORD"),
    ("NEFT/Electricity Board-5566/15-Aug-2024", "ELECTRICITY BOARD"),
    (
        "ACH/Netflix Subscription/netflix@hdfcbank/22-09-2024",
        "NETFLIX SUBSCRIPTION",
    ),
    (
        "BIL/NEFT/987654321098/Loan EMI/Jane Doe/SOME BANK",
        "LOAN EMI JANE DOE SOME BANK",
    ),
    ("MMT/IMPS/556677889900/Jane Smith/XYZB0001234", "JANE SMITH XYZB0001234"),
    ("BIL/INFT/Self Transfer/Internal Account", "SELF TRANSFER INTERNAL ACCOUNT"),
]


@pytest.mark.parametrize("raw,expected", NORMALIZER_CORPUS)
def test_normalize_merchant(raw, expected):
    assert normalize_merchant(raw) == expected
