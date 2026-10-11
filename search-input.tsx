"use client";

import { useId, useRef, useState, useEffect } from "react";
import { Search, LoaderCircle, X } from "lucide-react";

export interface SearchInputProps {
  onSearch: (query: string) => void;
  defaultValue?: string;
  loading?: boolean;
  debounceMs?: number;
  label?: string;
  placeholder?: string;
  id?: string;
  name?: string;
  disabled?: boolean;
  className?: string;
}

export function SearchInput({
  onSearch, defaultValue = "", loading = false, debounceMs = 300,
  label = "جست‌وجو در منو", placeholder = "جست‌وجوی شیرینی…",
  id, name = "q", disabled = false, className = "",
}: SearchInputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const [value, setValue] = useState(defaultValue);
  const input = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callback = useRef(onSearch);
  callback.current = onSearch;
  const composing = useRef(false);
  const cancel = () => {
    if (timer.current !== null) clearTimeout(timer.current);
    timer.current = null;
  };
  useEffect(() => () => {
    if (timer.current !== null) clearTimeout(timer.current);
  }, []);
  const schedule = (query: string) => {
    cancel();
    timer.current = setTimeout(() => {
      timer.current = null;
      callback.current(query);
    }, Math.max(0, debounceMs));
  };
  const clear = () => {
    cancel();
    setValue("");
    callback.current("");
    input.current?.focus();
  };

  return (
    <div dir="rtl" className={`font-sans text-start ${className}`}>
      <label htmlFor={inputId} className="mb-1 block text-sm text-muted-foreground">{label}</label>
      <div aria-busy={loading} className="relative flex h-12 items-center rounded-md border border-border bg-background text-foreground transition-colors duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background motion-reduce:transition-none">
        <span className="pointer-events-none absolute start-3 text-muted-foreground" aria-hidden="true">
          {loading ? <LoaderCircle className="size-5 animate-spin motion-reduce:animate-none" /> : <Search className="size-5" />}
        </span>
        <input ref={input} id={inputId} name={name} type="search" enterKeyHint="search"
          autoComplete="off" disabled={disabled} value={value} placeholder={placeholder}
          className="h-full w-full min-w-0 rounded-md bg-transparent ps-11 pe-14 text-start text-base md:text-sm supports-[-webkit-touch-callout:none]:text-base placeholder:text-muted-foreground focus-visible:outline-none disabled:opacity-50 [&::-webkit-search-cancel-button]:appearance-none [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:appearance-none"
          onChange={event => {
            const query = event.target.value;
            setValue(query);
            cancel();
            if (!composing.current) schedule(query);
          }}
          onCompositionStart={() => { composing.current = true; cancel(); }}
          onCompositionEnd={event => { composing.current = false; schedule(event.currentTarget.value); }}
          onKeyDown={event => {
            if (event.nativeEvent.isComposing || composing.current) return;
            if (event.key === "Enter") { event.preventDefault(); cancel(); callback.current(value); }
            if (event.key === "Escape") { event.preventDefault(); clear(); }
          }} />
        {value !== "" && <button type="button" disabled={disabled} onClick={clear}
          aria-label="پاک‌کردن جست‌وجو"
          className="absolute end-0.5 flex size-11 items-center justify-center rounded-md text-muted-foreground transition-colors duration-200 hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none disabled:opacity-50">
          <X className="size-5" aria-hidden="true" />
        </button>}
      </div>
      <span role="status" className="sr-only">{loading ? "در حال جست‌وجو…" : ""}</span>
    </div>
  );
}

export default SearchInput;
