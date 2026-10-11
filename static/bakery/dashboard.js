(() => {
  document.documentElement.classList.add("dashboard-js");
  const jalaliDate = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric", month: "long", day: "numeric",
  });
  document.querySelectorAll("[data-jalali-date]").forEach((time) => {
    const value = time.getAttribute("datetime");
    if (!value) return;
    const date = value.length === 10
      ? new Date(...value.split("-").map((part, index) => Number(part) - (index === 1 ? 1 : 0)))
      : new Date(value);
    if (!Number.isNaN(date.getTime())) time.textContent = jalaliDate.format(date);
  });

  let chartType = "bar";
  try { chartType = sessionStorage.getItem("dashboard-chart-type") === "line" ? "line" : "bar"; } catch (_) {}
  const readPoint = point => {
    const readout = document.querySelector(".chart-readout");
    if (readout && point) readout.textContent = `${point.dataset.day}: ${point.dataset.amount}`;
  };
  for (const type of ["focusin", "mouseover", "click"]) document.addEventListener(type, event => readPoint(event.target.closest(".chart-bar-group")));
  document.addEventListener("keydown", event => {
    const point = event.target.closest(".chart-bar-group");
    if (!point) return;
    if (["Enter", " "].includes(event.key)) { event.preventDefault(); readPoint(point); }
    if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const points = [...point.parentElement.querySelectorAll(".chart-bar-group")], index = points.indexOf(point);
      const next = event.key === "Home" ? 0 : event.key === "End" ? points.length-1 : (index + (event.key === "ArrowLeft" ? 1 : -1) + points.length) % points.length;
      points[next].focus();
    }
  });
  const applyChartType = () => {
    const svg = document.querySelector(".rtl-bar-chart");
    if (!svg) return;
    const axis = document.querySelector(".chart-fixed-axis");
    if (axis) {
      const fitAxis = () => {
        if (!axis.isConnected) return;
        const labels = [...axis.querySelectorAll("text")];
        const width = Math.ceil(Math.max(0, ...labels.map(label => label.getComputedTextLength()))) + 12;
        const height = axis.viewBox.baseVal.height;
        axis.setAttribute("viewBox", `0 0 ${width} ${height}`);
        axis.setAttribute("width", String(width));
        axis.style.width = `${width}px`;
        axis.style.flexBasis = `${width}px`;
        labels.forEach(label => label.setAttribute("x", String(width - 6)));
      };
      fitAxis();
      document.fonts?.ready.then(fitAxis);
    }
    const plot = svg.closest(".chart-plot-scroll");
    if (plot && !plot.dataset.initialized) {
      plot.dataset.initialized = "true";
      // RTL chronology runs oldest on right, newest on left. Start at latest.
      const showLatest = () => { plot.scrollLeft = -(plot.scrollWidth - plot.clientWidth); };
      requestAnimationFrame(showLatest);
      document.fonts?.ready.then(showLatest);
    }
    svg.dataset.type = chartType;
    try { sessionStorage.setItem("dashboard-chart-type", chartType); } catch (_) {}
    svg.setAttribute("aria-label", chartType === "line" ? "نمودار خطی فروش" : "نمودار میله‌ای فروش");
    document.querySelectorAll("[data-chart-type]").forEach(button => {
      const on = button.dataset.chartType === chartType;
      button.setAttribute("aria-checked", String(on)); button.tabIndex = on ? 0 : -1;
    });
  };
  document.querySelectorAll("[data-chart-type]").forEach(button => button.addEventListener("click", () => {
    chartType = button.dataset.chartType; applyChartType();
  }));
  document.querySelector(".chart-type-switch")?.addEventListener("keydown", event => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "bar" : event.key === "End" ? "line" : chartType === "bar" ? "line" : "bar";
    const button = document.querySelector(`[data-chart-type="${next}"]`);
    button.click(); button.focus();
  });
  applyChartType();
  const segments = document.querySelector(".sales-segments");
  if (segments) {
    const options = [...segments.querySelectorAll('[role="radio"]')];
    let selected = options.find(el => el.getAttribute("aria-checked") === "true");
    options.forEach(el => { el.tabIndex = el === selected ? 0 : -1; });
    const measure = () => {
      const pill = segments.querySelector(".sales-segment-pill");
      pill.style.width = `${selected.offsetWidth}px`;
      pill.style.transform = `translateX(${selected.offsetLeft - (segments.clientWidth - selected.offsetWidth)}px)`;
    };
    new ResizeObserver(measure).observe(segments);
    measure();
    const panel = segments.closest(".dashboard-chart");
    const feedback = document.createElement("p");
    feedback.setAttribute("role", "status");
    panel.append(feedback);
    let controller, sequence = 0;
    const selectPeriod = async (url, push = true) => {
      controller?.abort();
      controller = new AbortController();
      const current = ++sequence;
      panel.setAttribute("aria-busy", "true");
      feedback.textContent = "در حال دریافت آمار…";
      try {
        const response = await fetch(url, {credentials: "same-origin", signal: controller.signal});
        if (!response.ok) throw new Error("Request failed");
        const doc = new DOMParser().parseFromString(await response.text(), "text/html");
        const replacement = doc.querySelector(".dashboard-chart");
        if (!replacement) throw new Error("Missing chart");
        if (current !== sequence) return;
        for (const selector of [".dashboard-panel-head", ".chart-container", ".sales-data"]) {
          const node = replacement.querySelector(selector);
          if (!node) throw new Error("Missing chart section");
        }
        for (const selector of [".dashboard-panel-head", ".chart-container", ".sales-data"]) {
          panel.querySelector(selector).replaceWith(replacement.querySelector(selector));
        }
        applyChartType();
        const periodInput = document.querySelector('.dashboard-search input[name="period"]');
        if (periodInput) periodInput.value = new URL(url, location.href).searchParams.get("period") || "weekly";
        document.querySelector(".chart-readout").textContent = "برای دیدن مبلغ، یک نقطه را انتخاب کنید.";
        const period = new URL(url, location.href).searchParams.get("period") || "weekly";
        selected = options.find(el => new URL(el.href).searchParams.get("period") === period) || options[1];
        options.forEach(el => { el.setAttribute("aria-checked", String(el === selected)); el.tabIndex = el === selected ? 0 : -1; });
        measure();
        if (push) history.pushState({}, "", url);
        feedback.textContent = "آمار فروش به‌روز شد.";
      } catch (error) {
        if (error.name !== "AbortError" && current === sequence) feedback.textContent = "آمار دریافت نشد. بازه را دوباره انتخاب کنید.";
      } finally {
        if (current === sequence) panel.setAttribute("aria-busy", "false");
      }
    };
    options.forEach(option => option.addEventListener("click", event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      selectPeriod(option.href);
    }));
    window.addEventListener("popstate", () => selectPeriod(location.href, false));
    segments.addEventListener("keydown", event => {
      const current = options.indexOf(document.activeElement);
      const step = ["ArrowLeft", "ArrowDown"].includes(event.key) ? 1 : ["ArrowRight", "ArrowUp"].includes(event.key) ? -1 : 0;
      if (step || event.key === "Home" || event.key === "End") {
        event.preventDefault();
        const next = options[event.key === "Home" ? 0 : event.key === "End" ? options.length-1 : (current + step + options.length) % options.length];
        next.focus(); next.click();
      } else if (event.key === " ") { event.preventDefault(); document.activeElement.click(); }
    });
  }
  const menu = document.getElementById("dashboard-mobile-menu");
  const toggle = document.querySelector(".dashboard-menu-toggle");
  const closeButton = menu?.querySelector(".dashboard-menu-close");
  if (!menu || !toggle) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let menuMotion, menuClosing = false, savedOverflow = "";
  const animateMenu = (opening, immediate = false) => {
    menuMotion?.cancel();
    if (immediate || reducedMotion.matches || !menu.animate) return null;
    return menu.animate(opening
      ? [{transform: "translateX(100%)", opacity: .5}, {transform: "translateX(0)", opacity: 1}]
      : [{transform: getComputedStyle(menu).transform, opacity: 1}, {transform: "translateX(100%)", opacity: 0}],
      {duration: opening ? 240 : 160, easing: "cubic-bezier(.32,.72,0,1)"});
  };
  const close = (immediate = false) => {
    if (!menu.open || menuClosing) return;
    menuClosing = true;
    menu.classList.add("is-closing");
    menuMotion = animateMenu(false, immediate);
    const finish = () => {
      if (!menuClosing) return;
      menuClosing = false;
      menu.classList.remove("is-closing");
      menu.close();
    };
    if (menuMotion) menuMotion.finished.then(finish).catch(() => {}); else finish();
  };
  toggle.addEventListener("click", event => {
    menuClosing = false;
    menu.classList.remove("is-closing");
    if (!menu.open) { savedOverflow = document.body.style.overflow; menu.showModal(); }
    document.body.style.overflow = "hidden";
    toggle.setAttribute("aria-expanded", "true");
    menuMotion = animateMenu(true, event.detail === 0);
    closeButton?.focus();
  });
  closeButton?.addEventListener("click", event => close(event.detail === 0));
  menu.addEventListener("cancel", event => { event.preventDefault(); close(true); });
  menu.addEventListener("close", () => {
    menuMotion?.cancel();
    menuClosing = false;
    menu.classList.remove("is-closing");
    document.body.style.overflow = savedOverflow;
    toggle.setAttribute("aria-expanded", "false");
    if (toggle.getClientRects().length) toggle.focus();
  });
  menu.addEventListener("click", event => {
    if (event.target === menu) {
      const rect = menu.getBoundingClientRect();
      if (event.clientX < rect.x || event.clientX > rect.right || event.clientY < rect.y || event.clientY > rect.bottom) close();
    }
    if (event.target.closest?.("a")) close(true);
  });
  const breakpoint = window.matchMedia("(min-width: 901px)");
  breakpoint.addEventListener("change", () => {
    if (breakpoint.matches && menu.open) close(true);
  });
})();
