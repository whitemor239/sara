export function cn(...inputs: any[]): string {
  const classes: string[] = [];
  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === "string") {
      classes.push(input);
    } else if (Array.isArray(input)) {
      const inner = cn(...input);
      if (inner) classes.push(inner);
    } else if (typeof input === "object") {
      for (const key of Object.keys(input)) {
        if (input[key]) classes.push(key);
      }
    }
  }
  return classes.join(" ");
}

export function faNumber(value: number | string): string {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return String(value);
  const formatted = new Intl.NumberFormat("fa-IR").format(num);
  return formatted.replace(/,/g, "٬");
}

export function faPercent(value: number | string): string {
  const num = typeof value === "number" ? value : Number(value);
  if (Number.isNaN(num)) return `${value}٪`;
  const formatted = new Intl.NumberFormat("fa-IR").format(num);
  return `${formatted}٪`;
}

export function fa(value: number | string): string {
  return String(value).replace(/[0-9]/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[Number(d)]);
}

export function en(value: string): string {
  return value
    .replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String("٠١٢٣٤٥٦٧٨٩".indexOf(d)));
}

export function formatToman(value: number): string {
  return `${faNumber(value)} تومان`;
}
