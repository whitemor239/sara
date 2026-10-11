"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bell,
  Download,
  Home,
  Menu,
  Package,
  Plus,
  Search,
  Settings,
  ShoppingBag,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";

type StatKey = "sales" | "openOrders" | "newCustomers" | "averageBasket";
type StatValue = { value: number; delta?: number };
type OrderStatus = "paid" | "pending" | "preparing" | "ready" | "completed" | "cancelled";

export type DashboardOrder = {
  id: string;
  customer: string;
  amount: number;
  status: OrderStatus;
  href?: string;
};

export type DashboardData = {
  stats: Record<StatKey, StatValue>;
  weeklySales: readonly number[]; // From Saturday to Friday, in tomans.
  orders: readonly DashboardOrder[];
  monthlyGoal?: { current: number; target: number };
};

export type ShopDashboardProps = {
  data?: DashboardData;
  storeName?: string;
  managerName?: string;
  links?: Partial<{
    overview: string;
    orders: string;
    products: string;
    customers: string;
    settings: string;
    addProduct: string;
    account: string;
  }>;
};

/** Demonstration content only. Supply `data` from your own API in production. */
export const sampleDashboardData: DashboardData = {
  stats: {
    sales: { value: 12_450_000, delta: 18 },
    openOrders: { value: 246, delta: 12 },
    newCustomers: { value: 38, delta: -4 },
    averageBasket: { value: 1_860_000, delta: 6 },
  },
  weeklySales: [4_400_000, 6_200_000, 5_400_000, 7_800_000, 7_000_000, 9_600_000, 6_400_000],
  monthlyGoal: { current: 216_000_000, target: 300_000_000 },
  orders: [
    { id: "14052", customer: "مریم احمدی", amount: 2_890_000, status: "paid" },
    { id: "14051", customer: "علی رضایی", amount: 640_000, status: "pending" },
    { id: "14050", customer: "نگار کریمی", amount: 1_215_000, status: "ready" },
    { id: "14049", customer: "رضا موسوی", amount: 3_400_000, status: "preparing" },
  ],
};

const numberFormatter = new Intl.NumberFormat("fa-IR");
const persianDigits = (value: string | number) =>
  String(value).replace(/[0-9]/g, (digit) => "۰۱۲۳۴۵۶۷۸۹"[Number(digit)]);
const formatNumber = (value: number) => numberFormatter.format(value).replace(/,/g, "٬");
const formatToman = (value: number) => `${formatNumber(value)} تومان`;
const days = ["ش", "ی", "د", "س", "چ", "پ", "ج"] as const;
const weekdayNames = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"] as const;

const statuses: Record<OrderStatus, { label: string; classes: string }> = {
  paid: { label: "پرداخت‌شده", classes: "border-primary/30 bg-primary/10 text-primary" },
  pending: { label: "در انتظار پرداخت", classes: "border-border bg-muted text-foreground" },
  preparing: { label: "در حال آماده‌سازی", classes: "border-border bg-background text-foreground" },
  ready: { label: "آمادهٔ تحویل", classes: "border-primary/30 bg-primary/10 text-primary" },
  completed: { label: "تکمیل‌شده", classes: "border-border bg-muted text-muted-foreground" },
  cancelled: { label: "لغوشده", classes: "border-border bg-muted text-muted-foreground" },
};

const defaultLinks = {
  overview: "#overview",
  orders: "#orders",
  products: "/admin/bakery/product/",
  customers: "/admin/bakery/customerprofile/",
  settings: "/admin/",
  addProduct: "/admin/bakery/product/add/",
  account: "/admin/",
};

type NavLink = { label: string; href: string; icon: LucideIcon; count?: number; active?: boolean };

function NavItem({ item, onNavigate }: { item: NavLink; onNavigate?: () => void }) {
  const Icon = item.icon;
  return (
    <a
      href={item.href}
      onClick={onNavigate}
      aria-current={item.active ? "page" : undefined}
      className={`flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm transition-colors duration-200 motion-reduce:transition-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
        item.active
          ? "bg-primary/10 font-semibold text-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      <Icon aria-hidden="true" className="size-4 shrink-0" strokeWidth={1.8} />
      <span className="flex-1">{item.label}</span>
      {item.count !== undefined && (
        <span className="min-w-6 rounded-md bg-muted px-1.5 py-0.5 text-center text-xs tabular-nums text-foreground">
          {formatNumber(item.count)}
        </span>
      )}
    </a>
  );
}

function SidebarContent({
  storeName,
  managerName,
  items,
  accountHref,
  onNavigate,
}: {
  storeName: string;
  managerName: string;
  items: { overview: NavLink; sales: NavLink[]; account: NavLink[] };
  accountHref: string;
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="border-b border-border px-5 py-6">
        <p className="text-lg font-bold leading-tight text-foreground">{storeName}</p>
        <p className="mt-1 text-xs text-muted-foreground">مدیریت فروشگاه</p>
      </div>
      <nav aria-label="ناوبری داشبورد" className="flex-1 space-y-6 px-3 py-5">
        <NavItem item={items.overview} onNavigate={onNavigate} />
        <div>
          <p className="px-3 pb-2 text-xs font-medium text-muted-foreground">فروش</p>
          <div className="space-y-1">{items.sales.map((item) => <NavItem key={item.label} item={item} onNavigate={onNavigate} />)}</div>
        </div>
        <div>
          <p className="px-3 pb-2 text-xs font-medium text-muted-foreground">حساب</p>
          <div className="space-y-1">{items.account.map((item) => <NavItem key={item.label} item={item} onNavigate={onNavigate} />)}</div>
        </div>
      </nav>
      <a
        href={accountHref}
        onClick={onNavigate}
        className="flex min-h-16 items-center gap-3 border-t border-border px-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-primary"
      >
        <span aria-hidden="true" className="grid size-9 shrink-0 place-items-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
          {managerName.slice(0, 1)}
        </span>
        <span className="min-w-0 truncate text-sm font-medium">{managerName}</span>
      </a>
    </>
  );
}

function StatTile({ label, value, unit, delta, prominent }: {
  label: string;
  value: number;
  unit?: string;
  delta?: number;
  prominent?: boolean;
}) {
  return (
    <article className={`flex min-h-36 flex-col justify-between rounded-xl p-5 ${prominent ? "bg-primary text-primary-foreground" : "border border-border bg-card text-foreground"}`}>
      <p className={`text-sm ${prominent ? "text-primary-foreground/80" : "text-muted-foreground"}`}>{label}</p>
      <div>
        <p className="text-2xl font-bold tabular-nums sm:text-3xl">
          {formatNumber(value)}{unit && <span className="ms-1.5 text-xs font-normal">{unit}</span>}
        </p>
        {delta !== undefined && (
          <p className={`mt-1 text-xs tabular-nums ${prominent ? "text-primary-foreground/80" : "text-muted-foreground"}`}>
            {delta > 0 ? "+" : delta < 0 ? "−" : ""}{formatNumber(Math.abs(delta))}٪ نسبت به دورهٔ قبل
          </p>
        )}
      </div>
    </article>
  );
}

function WeeklyChart({ values }: { values: readonly number[] }) {
  const week = days.map((day, index) => ({ day, amount: values[index] ?? 0 }));
  const peak = Math.max(...week.map(({ amount }) => amount), 1);
  const highest = week.findIndex(({ amount }) => amount === peak);

  return (
    <section aria-labelledby="weekly-sales-title" className="rounded-xl border border-border bg-card p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 id="weekly-sales-title" className="font-semibold">فروش هفتگی</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">مبلغ فروش به تفکیک روز، به تومان</p>
        </div>
        <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">هفت روز اخیر</span>
      </div>
      <figure className="mt-7">
        <ul className="grid grid-cols-7 items-end gap-2 border-b border-border sm:gap-4" aria-label="نمودار میله‌ای فروش از شنبه تا جمعه">
          {week.map(({ day, amount }, index) => (
            <li key={index} className="min-w-0 text-center">
              <div className="flex h-36 items-end justify-center" title={`${day}: ${formatToman(amount)}`}>
                <div
                  aria-hidden="true"
                  className={`w-full max-w-12 rounded-t-md ${index === highest ? "bg-primary" : "bg-primary/20"}`}
                  style={{ height: amount ? `${Math.max(5, Math.round((amount / peak) * 100))}%` : "0%" }}
                />
              </div>
              <span className="sr-only">{weekdayNames[index]}: {formatToman(amount)}</span>
            </li>
          ))}
        </ul>
        <figcaption className="mt-3 grid grid-cols-7 gap-2 text-center text-xs text-muted-foreground sm:gap-4">
          {days.map((day, index) => <span key={index}>{day}</span>)}
        </figcaption>
      </figure>
    </section>
  );
}

function GoalPanel({ goal }: { goal?: DashboardData["monthlyGoal"] }) {
  if (!goal) return null;
  const percent = goal.target > 0 ? Math.min(100, Math.max(0, Math.round((goal.current / goal.target) * 100))) : 0;
  return (
    <section aria-labelledby="monthly-goal-title" className="flex flex-col justify-between rounded-xl border border-border bg-card p-5 sm:p-6">
      <div>
        <h2 id="monthly-goal-title" className="font-semibold">هدف ماهانه</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">پیشرفت فروش این ماه</p>
      </div>
      <div className="mt-8">
        <p className="text-3xl font-semibold tabular-nums">{formatNumber(percent)}٪</p>
        <div
          role="progressbar"
          aria-label="پیشرفت هدف ماهانه"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          aria-valuetext={`${formatNumber(percent)} درصد`}
          className="mt-4 h-2 overflow-hidden rounded-full bg-muted"
        >
          <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
        </div>
        <div className="mt-3 flex flex-wrap justify-between gap-1 text-xs text-muted-foreground">
          <span>{formatToman(goal.current)}</span><span>از {formatToman(goal.target)}</span>
        </div>
      </div>
    </section>
  );
}

function StatusBadge({ status }: { status: OrderStatus }) {
  const { label, classes } = statuses[status];
  return <span className={`inline-flex whitespace-nowrap rounded-md border px-2.5 py-1 text-xs ${classes}`}>{label}</span>;
}

function downloadOrders(orders: readonly DashboardOrder[]) {
  const quote = (value: string) => {
    const safeValue = /^[\s\u0000-\u001f]*[=+@-]/.test(value) ? `'${value}` : value;
    return `"${safeValue.replaceAll('"', '""')}"`;
  };
  const lines = [
    ["شماره سفارش", "مشتری", "مبلغ (تومان)", "وضعیت"],
    ...orders.map((order) => [order.id, order.customer, String(order.amount), statuses[order.status].label]),
  ];
  const csv = `\uFEFF${lines.map((line) => line.map(quote).join(",")).join("\r\n")}`;
  const objectUrl = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = "sefaresh-ha.csv";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

const focusStyle = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";

/** RTL shop dashboard template. Replace the demonstration data with live server data. */
export function ShopDashboard({ data, storeName = "تِیستی‌توم", managerName = "مدیر فروشگاه", links }: ShopDashboardProps) {
  const dashboard = data ?? sampleDashboardData;
  const isSample = data === undefined;
  const routes = { ...defaultLinks, ...links };
  const [search, setSearch] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const notifications = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (menuOpen && !element.open) element.showModal();
    if (!menuOpen && element.open) element.close();
  }, [menuOpen]);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 1024px)");
    const onDesktopChange = () => { if (desktop.matches) setMenuOpen(false); };
    desktop.addEventListener("change", onDesktopChange);
    return () => desktop.removeEventListener("change", onDesktopChange);
  }, []);

  useEffect(() => {
    if (!notificationsOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setNotificationsOpen(false);
    };
    const onPointerDown = (event: PointerEvent) => {
      if (notifications.current && !notifications.current.contains(event.target as Node)) setNotificationsOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [notificationsOpen]);

  const query = search.trim().toLocaleLowerCase("fa-IR");
  const filteredOrders = useMemo(() => dashboard.orders.filter((order) => {
    const searchable = `${order.id} ${persianDigits(order.id)} ${order.customer} ${statuses[order.status].label}`;
    return searchable.toLocaleLowerCase("fa-IR").includes(query);
  }), [dashboard.orders, query]);

  const navItems = {
    overview: { label: "نمای کلی", href: routes.overview, icon: Home, active: true },
    sales: [
      { label: "سفارش‌ها", href: routes.orders, icon: ShoppingBag, count: dashboard.stats.openOrders.value },
      { label: "محصولات", href: routes.products, icon: Package },
      { label: "مشتریان", href: routes.customers, icon: Users, count: dashboard.stats.newCustomers.value },
    ],
    account: [{ label: "تنظیمات", href: routes.settings, icon: Settings }],
  };

  const today = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  }).format(new Date());

  return (
    <div
      dir="rtl"
      lang="fa"
      style={{ fontSynthesis: "none" }}
      className="flex min-h-dvh bg-background font-['Vazirmatn','Vazir',sans-serif] text-foreground tracking-normal"
    >
      <aside className="hidden h-dvh w-60 shrink-0 flex-col border-e border-border bg-card lg:sticky lg:top-0 lg:flex">
        <SidebarContent storeName={storeName} managerName={managerName} items={navItems} accountHref={routes.account} />
      </aside>

      <dialog
        ref={dialog}
        aria-label="فهرست مدیریت فروشگاه"
        onClose={() => setMenuOpen(false)}
        onClick={(event) => { if (event.target === dialog.current) setMenuOpen(false); }}
        className="ms-0 me-auto h-dvh max-h-dvh w-72 max-w-[85vw] flex-col border-0 border-e border-border bg-card p-0 text-foreground backdrop:bg-foreground/40 open:flex lg:hidden"
      >
        <div className="flex justify-end px-4 pt-3">
          <button type="button" onClick={() => setMenuOpen(false)} aria-label="بستن منو" className={`grid size-11 place-items-center rounded-lg hover:bg-muted ${focusStyle}`}>
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        <SidebarContent storeName={storeName} managerName={managerName} items={navItems} accountHref={routes.account} onNavigate={() => setMenuOpen(false)} />
      </dialog>

      <div className="min-w-0 flex-1">
        <header className="flex min-h-16 items-center justify-between gap-3 border-b border-border bg-card px-4 sm:px-8">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <button type="button" onClick={() => setMenuOpen(true)} aria-label="باز کردن منو" className={`grid size-11 shrink-0 place-items-center rounded-lg hover:bg-muted lg:hidden ${focusStyle}`}>
              <Menu aria-hidden="true" className="size-5" />
            </button>
            <label htmlFor="order-search" className="sr-only">جست‌وجو در سفارش‌ها</label>
            <div className="relative w-full max-w-sm">
              <Search aria-hidden="true" className="pointer-events-none absolute inset-y-0 start-0 my-auto ms-3 size-4 text-muted-foreground" />
              <input
                id="order-search"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="جست‌وجو در سفارش‌ها…"
                className={`h-10 w-full rounded-lg border border-border bg-background ps-10 pe-3 text-base text-foreground placeholder:text-muted-foreground sm:text-sm supports-[-webkit-touch-callout:none]:text-base ${focusStyle}`}
              />
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <div ref={notifications} className="relative">
              <button
                type="button"
                aria-label="اعلان‌ها"
                aria-expanded={notificationsOpen}
                aria-controls="dashboard-notifications"
                onClick={() => setNotificationsOpen((open) => !open)}
                className={`grid size-10 place-items-center rounded-lg hover:bg-muted ${focusStyle}`}
              >
                <Bell aria-hidden="true" className="size-5" strokeWidth={1.8} />
              </button>
              {notificationsOpen && (
                <div id="dashboard-notifications" className="absolute end-0 z-20 mt-2 w-64 rounded-xl border border-border bg-card p-4">
                  <p className="text-sm font-semibold">اعلان‌ها</p>
                  <p className="mt-2 text-xs leading-6 text-muted-foreground">اعلان تازه‌ای برای نمایش وجود ندارد.</p>
                </div>
              )}
            </div>
            <a href={routes.account} aria-label="حساب مدیر فروشگاه" className={`grid size-9 place-items-center rounded-full bg-primary/10 text-sm font-semibold text-primary ${focusStyle}`}>
              <span aria-hidden="true">{managerName.slice(0, 1)}</span>
            </a>
          </div>
        </header>

        <main id="overview" className="mx-auto max-w-7xl space-y-7 px-4 py-7 sm:px-8 sm:py-9">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-xs text-muted-foreground">{today}</p>
              <h1 className="mt-1 text-2xl font-bold sm:text-3xl">نمای کلی فروشگاه</h1>
              {isSample && <p className="mt-1 text-xs text-muted-foreground">داده‌های نمایشی برای پیش‌نمایش قالب</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => downloadOrders(filteredOrders)}
                disabled={!filteredOrders.length}
                className={`inline-flex min-h-10 items-center gap-2 rounded-lg border border-border bg-card px-3 text-sm hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50 ${focusStyle}`}
              >
                <Download aria-hidden="true" className="size-4" />
                دریافت فهرست
              </button>
              <a href={routes.addProduct} className={`inline-flex min-h-10 items-center gap-2 rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground hover:opacity-90 ${focusStyle}`}>
                <Plus aria-hidden="true" className="size-4" />
                محصول جدید
              </a>
            </div>
          </div>

          <section aria-label="آمار فروشگاه" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="فروش امروز" {...dashboard.stats.sales} unit="تومان" prominent />
            <StatTile label="سفارش‌های باز" {...dashboard.stats.openOrders} />
            <StatTile label="مشتریان جدید" {...dashboard.stats.newCustomers} />
            <StatTile label="میانگین سبد" {...dashboard.stats.averageBasket} unit="تومان" />
          </section>

          <div className={`grid gap-4 ${dashboard.monthlyGoal ? "lg:grid-cols-5" : ""}`}>
            <div className={dashboard.monthlyGoal ? "lg:col-span-3" : ""}><WeeklyChart values={dashboard.weeklySales} /></div>
            {dashboard.monthlyGoal && <div className="lg:col-span-2"><GoalPanel goal={dashboard.monthlyGoal} /></div>}
          </div>

          <section id="orders" aria-labelledby="recent-orders-title" className="scroll-mt-6">
            <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
              <h2 id="recent-orders-title" className="text-lg font-semibold">سفارش‌های اخیر</h2>
              <span aria-live="polite" className="text-xs text-muted-foreground">{formatNumber(filteredOrders.length)} سفارش</span>
            </div>
            <div className="overflow-x-auto rounded-xl border border-border bg-card">
              <table className="w-full min-w-[35rem] border-collapse text-sm">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-start font-medium sm:px-5">شماره</th>
                    <th scope="col" className="px-4 py-3 text-start font-medium sm:px-5">مشتری</th>
                    <th scope="col" className="px-4 py-3 text-start font-medium sm:px-5">مبلغ</th>
                    <th scope="col" className="px-4 py-3 text-start font-medium sm:px-5">وضعیت</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.id} className="border-t border-border transition-colors duration-150 motion-reduce:transition-none hover:bg-muted/40">
                      <td className="px-4 py-4 sm:px-5">
                        {order.href ? (
                          <a href={order.href} className={`font-medium text-primary underline-offset-4 hover:underline ${focusStyle}`}>#{persianDigits(order.id)}</a>
                        ) : (
                          <span className="font-medium tabular-nums">#{persianDigits(order.id)}</span>
                        )}
                      </td>
                      <td className="px-4 py-4 sm:px-5">{order.customer}</td>
                      <td className="whitespace-nowrap px-4 py-4 tabular-nums sm:px-5">{formatToman(order.amount)}</td>
                      <td className="px-4 py-4 sm:px-5"><StatusBadge status={order.status} /></td>
                    </tr>
                  ))}
                  {!filteredOrders.length && (
                    <tr><td colSpan={4} className="px-5 py-10 text-center text-muted-foreground">
                      {dashboard.orders.length ? "سفارشی با این جست‌وجو پیدا نشد." : "هنوز سفارشی ثبت نشده است."}
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
            {search && <button type="button" onClick={() => setSearch("")} className={`mt-3 text-sm text-primary underline-offset-4 hover:underline ${focusStyle}`}>پاک‌کردن جست‌وجو</button>}
          </section>
        </main>
      </div>
    </div>
  );
}

export default ShopDashboard;
