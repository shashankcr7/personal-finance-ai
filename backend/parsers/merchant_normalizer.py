import re

BANK_PREFIX_RE = re.compile(r"^(?:(?:UPI|IMPS|NEFT|ACH|BIL|MMT|INFT)[/\-]+){1,2}")
UPI_HANDLE_RE = re.compile(r"\b[\w.\-]+@[\w]+\b")
DATE_RE = re.compile(
    r"\b\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}\b" r"|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"
)
REF_ID_RE = re.compile(r"\b\d{5,}\b")
TRAILING_NUM_SUFFIX_RE = re.compile(r"-\d+\b")
SEPARATORS_RE = re.compile(r"[/\-_]+")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_merchant(description: str) -> str:
    text = description.upper()
    text = BANK_PREFIX_RE.sub(" ", text)
    text = UPI_HANDLE_RE.sub(" ", text)
    text = DATE_RE.sub(" ", text)
    text = REF_ID_RE.sub(" ", text)
    text = TRAILING_NUM_SUFFIX_RE.sub("", text)
    text = SEPARATORS_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()
