(() => {
  const digits = value => value.replace(/[۰-۹٠-٩]/g, character => {
    const persian = "۰۱۲۳۴۵۶۷۸۹".indexOf(character);
    return String(persian >= 0 ? persian : "٠١٢٣٤٥٦٧٨٩".indexOf(character));
  });
  const format = input => {
    const value = digits(input.value);
    const raw = value.replace(/[,٬\s]/g, "");
    // Leave malformed or negative values intact for server-side validation.
    if (!/^\d*$/.test(raw)) return;
    const caret = input.selectionStart;
    const before = caret === null ? null : (value.slice(0, caret).match(/\d/g) || []).length;
    const formatted = raw.replace(/\B(?=(\d{3})+(?!\d))/g, "٬");
    if (input.value === formatted) return;
    input.value = formatted;
    if (document.activeElement === input && before !== null) {
      let position = 0, seen = 0;
      while (position < formatted.length && seen < before) {
        if (/\d/.test(formatted[position])) seen++;
        position++;
      }
      input.setSelectionRange(position, position);
    }
  };
  document.addEventListener("input", event => {
    if (event.target.matches("input[data-money-input]")) format(event.target);
  });
  const initialize = () => document.querySelectorAll("input[data-money-input]").forEach(format);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
