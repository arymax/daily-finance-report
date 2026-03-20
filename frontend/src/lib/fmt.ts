export const twd = (v: number) =>
  new Intl.NumberFormat("zh-TW", {
    style: "currency",
    currency: "TWD",
    maximumFractionDigits: 0,
  }).format(v);

export const pct = (v: number, digits = 1) =>
  `${v >= 0 ? "+" : ""}${v.toFixed(digits)}%`;

export const num = (v: number, digits = 2) => v.toFixed(digits);

export const sign = (v: number) => (v >= 0 ? "text-emerald-400" : "text-red-400");
