import * as React from "react";
import { ChevronRight, ChevronLeft, Ellipsis } from "lucide-react";

export function paginationItems(current: number, total: number): Array<number | null> {
  const selected = new Set([1, total]);
  for (let page = Math.max(1, current - 1); page <= Math.min(total, current + 1); page++) selected.add(page);
  const pages = [...selected].filter(page => page >= 1 && page <= total).sort((a, b) => a - b);
  const result: Array<number | null> = [];
  pages.forEach((page, index) => {
    const previous = pages[index - 1];
    if (index && page - previous === 2) result.push(previous + 1);
    else if (index && page - previous > 2) result.push(null);
    result.push(page);
  });
  return result;
}

export interface PaginationProps {
  currentPage: number;
  totalPages: number;
  /** Django URL builder: preserve filters and return server page URLs. */
  hrefForPage: (page: number) => string;
  className?: string;
}

const numberFormat = new Intl.NumberFormat("fa-IR");
const linkStyle = "inline-flex min-h-11 min-w-11 items-center justify-center gap-2 rounded-md border border-border px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-colors duration-150 motion-reduce:transition-none";

export function Pagination({ currentPage, totalPages, hrefForPage, className = "" }: PaginationProps) {
  if (!Number.isInteger(totalPages) || totalPages < 2) return null;
  const current = Math.min(totalPages, Math.max(1, Math.trunc(currentPage) || 1));
  return (
    <nav dir="rtl" aria-label="صفحه‌بندی" className={`font-sans ${className}`}>
      <ul className="flex flex-wrap items-center justify-center gap-2 text-foreground">
        <li>{current > 1 ? <a className={`${linkStyle} bg-background`} href={hrefForPage(current - 1)} rel="prev"><ChevronRight aria-hidden="true" size={18} />قبلی</a> : <span aria-disabled="true" className={`${linkStyle} bg-background text-muted-foreground`}><ChevronRight aria-hidden="true" size={18} />قبلی</span>}</li>
        {paginationItems(current, totalPages).map((page, index) => (
          <li key={page ?? `gap-${index}`}>
            {page === null ? <span className="inline-flex min-h-11 min-w-11 items-center justify-center text-muted-foreground"><Ellipsis aria-hidden="true" size={18} /><span className="sr-only">صفحه‌های دیگر</span></span> :
              <a href={hrefForPage(page)} aria-label={`صفحهٔ ${numberFormat.format(page)}`} aria-current={page === current ? "page" : undefined} className={`${linkStyle} ${page === current ? "bg-primary text-primary-foreground" : "bg-background text-foreground hover:bg-muted"}`}>{numberFormat.format(page)}</a>}
          </li>
        ))}
        <li>{current < totalPages ? <a className={`${linkStyle} bg-background`} href={hrefForPage(current + 1)} rel="next">بعدی<ChevronLeft aria-hidden="true" size={18} /></a> : <span aria-disabled="true" className={`${linkStyle} bg-background text-muted-foreground`}>بعدی<ChevronLeft aria-hidden="true" size={18} /></span>}</li>
      </ul>
    </nav>
  );
}
