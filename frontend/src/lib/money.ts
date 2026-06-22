// Pure string formatting only - never Number()/parseFloat() on a money value.
// The backend computes every figure; this module only changes how the same
// decimal string is displayed (digit grouping + symbol), never its value.

function groupIndian(integerDigits: string): string {
  const isNegative = integerDigits.startsWith("-");
  const digits = isNegative ? integerDigits.slice(1) : integerDigits;

  if (digits.length <= 3) {
    return (isNegative ? "-" : "") + digits;
  }

  const lastThree = digits.slice(-3);
  let remaining = digits.slice(0, -3);
  const groups: string[] = [];
  while (remaining.length > 2) {
    groups.unshift(remaining.slice(-2));
    remaining = remaining.slice(0, -2);
  }
  if (remaining.length > 0) {
    groups.unshift(remaining);
  }

  return (isNegative ? "-" : "") + [...groups, lastThree].join(",");
}

/** Formats a decimal string like "1500000.00" as "₹15,00,000.00". */
export function formatINR(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const [intPart, decPart = "00"] = value.split(".");
  const grouped = groupIndian(intPart);
  return `₹${grouped}.${decPart.padEnd(2, "0").slice(0, 2)}`;
}

/** Formats a decimal percentage string like "56.00" as "56.00%". */
export function formatPercent(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${value}%`;
}

/** Formats a signed percentage delta string like "-9.00" as "-9.00%", "+25.00%". */
export function formatDelta(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const isNegative = value.startsWith("-");
  return isNegative ? `${value}%` : `+${value}%`;
}
