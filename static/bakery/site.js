(() => {
  document.documentElement.classList.add("js");
  const modalState = new WeakMap();
  const modal = (element, open, trigger) => {
    if (!element) return;
    if (open) {
      const blocked = [];
      let branch = element;
      while (branch.parentElement && branch.parentElement !== document.documentElement) {
        for (const sibling of branch.parentElement.children) {
          if (sibling !== branch && !sibling.inert && !sibling.className?.includes?.("backdrop")) {
            sibling.inert = true;
            blocked.push(sibling);
          }
        }
        branch = branch.parentElement;
      }
      modalState.set(element, { blocked, trigger, overflow: document.body.style.overflow });
      element.inert = false;
      element.setAttribute("aria-hidden", "false");
      document.body.style.overflow = "hidden";
      element.querySelector("button, a[href], input")?.focus();
    } else {
      const state = modalState.get(element);
      if (!state) return;
      state.blocked.forEach(node => { node.inert = false; });
      document.body.style.overflow = state.overflow;
      state.trigger?.focus();
      element.inert = true;
      element.setAttribute("aria-hidden", "true");
      modalState.delete(element);
    }
  };
  document.addEventListener("keydown", event => {
    if (event.key !== "Tab") return;
    const dialog = document.querySelector('[role="dialog"][aria-hidden="false"]');
    if (!dialog) return;
    const nodes = [...dialog.querySelectorAll('button, a[href], input, [tabindex="0"]')]
      .filter(node => !node.disabled && node.getClientRects().length);
    const first = nodes[0], last = nodes[nodes.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  });
  const header = document.querySelector(".site-header-wrapper");
  const headerSentinel = document.querySelector("[data-header-sentinel]");
  if (header && headerSentinel && "IntersectionObserver" in window) {
    new IntersectionObserver(([entry]) => {
      header.classList.toggle("is-scrolled", !entry.isIntersecting);
    }, { rootMargin: "8px 0px 0px 0px" }).observe(headerSentinel);
  }
  const bottomNav = document.querySelector(".mobile-bottom-nav");
  const measureNavigation = () => {
    document.documentElement.style.setProperty("--header-height", `${header?.getBoundingClientRect().height || 0}px`);
    document.documentElement.style.setProperty("--bottom-nav-height", `${bottomNav?.getBoundingClientRect().height || 0}px`);
  };
  const navObserver = new ResizeObserver(measureNavigation);
  [header, bottomNav].filter(Boolean).forEach(node => navObserver.observe(node));
  measureNavigation();

  const searchToggle = document.querySelector(".header-search-toggle");
  const searchPanel = document.querySelector(".header-search-panel");
  const searchFrost = document.querySelector(".search-frost-backdrop");
  const closeSearch = () => {
    if (!searchPanel || searchPanel.hidden) return;
    searchPanel.hidden = true;
    if (searchFrost) searchFrost.hidden = true;
    searchToggle.setAttribute("aria-expanded", "false");
    searchToggle.focus();
  };
  searchToggle?.addEventListener("click", () => {
    if (!searchPanel.hidden) { closeSearch(); return; }
    searchPanel.hidden = false;
    if (searchFrost) searchFrost.hidden = false;
    searchToggle.setAttribute("aria-expanded", "true");
    searchPanel.querySelector("input").focus();
  });
  searchPanel?.querySelector("[data-search-close]").addEventListener("click", closeSearch);
  document.addEventListener("keydown", event => { if (event.key === "Escape") closeSearch(); });
  document.addEventListener("click", event => {
    if (!searchPanel?.contains(event.target) && !searchToggle?.contains(event.target)) closeSearch();
  });
  const menuButton = document.querySelector(".menu-toggle");
  const navDrawer = document.getElementById("mobile-nav-drawer");
  const navBackdrop = document.getElementById("mobile-nav-backdrop");
  const navDrawerClose = navDrawer?.querySelector(".nav-drawer-close");

  if (menuButton && navDrawer && navBackdrop) {
    const setDrawerOpen = (isOpen) => {
      if (isOpen) closeSearch();
      navDrawer.classList.toggle("is-open", isOpen);
      navBackdrop.classList.toggle("is-open", isOpen);
      modal(navDrawer, isOpen, menuButton);
      navBackdrop.setAttribute("aria-hidden", String(!isOpen));
      menuButton.setAttribute("aria-expanded", String(isOpen));
      if (isOpen) navDrawerClose?.focus();
      else if (!menuButton.getClientRects().length) searchToggle?.focus();
    };

    menuButton.addEventListener("click", () => setDrawerOpen(true));
    navDrawerClose?.addEventListener("click", () => setDrawerOpen(false));
    navBackdrop.addEventListener("click", () => setDrawerOpen(false));

    navDrawer.addEventListener("click", (event) => {
      if (event.target.closest("a")) setDrawerOpen(false);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && navDrawer.classList.contains("is-open")) {
        setDrawerOpen(false);
        menuButton.focus();
      }
    });

    window.matchMedia("(min-width: 64rem)").addEventListener("change", event => {
      if (event.matches && !menuButton.getClientRects().length && navDrawer.classList.contains("is-open")) setDrawerOpen(false);
    });
  }

  // Delegate submissions so filtered product cards work without rebinding.
  let cartQueue = Promise.resolve();
  const cartStatus = document.createElement("div");
  cartStatus.className = "cart-live-status";
  cartStatus.setAttribute("role", "status");
  cartStatus.setAttribute("aria-live", "polite");
  cartStatus.hidden = true;
  document.body.append(cartStatus);
  let statusTimer;
  document.addEventListener("submit", event => {
    const form = event.target.closest("form[data-cart-add]");
    if (!form) return;
    event.preventDefault();
    if (form.dataset.pending) return;
    form.dataset.pending = "true";
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    form.setAttribute("aria-busy", "true");
    const body = new FormData(form);
    cartQueue = cartQueue.then(async () => {
      try {
        const response = await fetch(form.action, {
          method: "POST", body, credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const count = String(data.cart_count).replace(/[0-9]/g, digit => "۰۱۲۳۴۵۶۷۸۹"[digit]);
        document.querySelectorAll(".basket-count").forEach(node => { node.textContent = count; });
        let badge = document.querySelector(".mobile-bottom-badge");
        if (!badge) {
          badge = document.createElement("span");
          badge.className = "mobile-bottom-badge";
          document.querySelector(".mobile-bottom-basket .mobile-bottom-icon-wrap")?.append(badge);
        }
        badge.textContent = count;
        badge.style.display = data.cart_count > 0 ? "" : "none";
        badge.setAttribute("aria-label", `${count} قلم در سبد خرید`);
        cartStatus.textContent = data.message;
      } catch (error) {
        // Never resend automatically: server may have accepted POST before connection failed.
        cartStatus.textContent = "پاسخ سبد دریافت نشد. پیش از تلاش دوباره، سبد خرید را بررسی کنید.";
      } finally {
        clearTimeout(statusTimer);
        cartStatus.hidden = false;
        statusTimer = setTimeout(() => { cartStatus.hidden = true; }, 5000);
        button.disabled = false;
        form.removeAttribute("aria-busy");
        delete form.dataset.pending;
      }
    });
  });

  const basket = document.querySelector("#basket-content");
  if (basket) {
    document.body.classList.add("has-basket");
    const fa = value => String(value).replace(/[0-9]/g, d => "۰۱۲۳۴۵۶۷۸۹"[d]);
    const ascii = value => value.replace(/[۰-۹٠-٩]/g, d => String("۰۱۲۳۴۵۶۷۸۹".includes(d) ? "۰۱۲۳۴۵۶۷۸۹".indexOf(d) : "٠١٢٣٤٥٦٧٨٩".indexOf(d)));
    const money = value => new Intl.NumberFormat("fa-IR").format(value) + " تومان";
    let pending = false, undo = null;
    const undoButton = document.querySelector("#basket-undo");
    const feedback = document.querySelector(".basket-feedback span");
    const syncQuantityLimits = () => {
      basket.querySelectorAll(".quantity-stepper").forEach(control => {
        const input = control.querySelector('[name="quantity"]');
        control.querySelector('[data-step="1"]').disabled = pending || Number(input.dataset.saved) >= 99;
        control.querySelector('[data-step="-1"]').disabled = pending || Number(input.dataset.saved) <= 0;
      });
    };
    const popQuantity = input => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      input.classList.remove("quantity-pop");
      void input.offsetWidth;
      input.classList.add("quantity-pop");
    };
    const guardCheckout = () => {
      const dirty = [...basket.querySelectorAll('[name="quantity"]')].some(input => !input.closest(".basket-item").hidden && ascii(input.value) !== input.dataset.saved);
      document.querySelectorAll("[data-basket-checkout]").forEach(link => { link.setAttribute("aria-disabled", String(pending || dirty)); });
    };
    const apply = data => {
      basket.querySelectorAll(".basket-item").forEach(row => {
        const itemKey = row.dataset.itemKey || row.dataset.productId;
        const item = data.items.find(item => String(item.key || item.id) === itemKey);
        row.hidden = !item;
        if (item) {
          const input = row.querySelector('[name="quantity"]');
          if (Number(input.dataset.saved) !== item.quantity) popQuantity(input);
          input.value = fa(item.quantity); input.dataset.saved = String(item.quantity);
          row.querySelector(".basket-line-total").textContent = money(item.line_total);
        }
      });
      document.querySelectorAll("[data-basket-total]").forEach(node => { node.textContent = money(data.total); });
      document.querySelectorAll(".basket-count,.mobile-bottom-badge").forEach(node => { node.textContent = fa(data.cart_count); });
      document.querySelectorAll(".mobile-bottom-badge").forEach(node => {
        node.style.display = data.cart_count > 0 ? "" : "none";
        node.setAttribute("aria-label", `${fa(data.cart_count)} قلم در سبد خرید`);
      });
      basket.querySelector(".basket-empty").hidden = !!data.items.length;
      document.querySelector(".basket-summary").hidden = !data.items.length;
      document.querySelector(".basket-mobile-checkout").hidden = !data.items.length;
    };
    const send = async (form, removing = false, restoring = null) => {
      if (pending) return;
      const row = form.closest(".basket-item"), input = row.querySelector('[name="quantity"]');
      const quantity = restoring ?? Number(ascii(input.value));
      const error = row.querySelector(".basket-item-error");
      if (!removing && (!Number.isInteger(quantity) || quantity < 0 || quantity > 99 || !ascii(input.value).trim())) {
        error.textContent = "تعداد باید بین ۰ و ۹۹ باشد."; input.focus(); return;
      }
      const deleting = removing || quantity === 0;
      error.textContent = "";
      const body = new FormData(form);
      if (!removing) body.set("quantity", String(quantity));
      pending = true; guardCheckout();
      basket.setAttribute("aria-busy", "true");
      basket.querySelectorAll("button,input:not([type=hidden])").forEach(node => { node.disabled = true; });
      undoButton.disabled = true;
      try {
        const response = await fetch(form.action, {method:"POST", body, credentials:"same-origin", headers:{"X-Requested-With":"XMLHttpRequest"}});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        if (deleting) { undo = {form: row.querySelector("[data-basket-update]"), quantity: Number(input.dataset.saved)}; undoButton.hidden = false; }
        if (restoring !== null) { undo = null; undoButton.hidden = true; }
        apply(data);
        feedback.textContent = deleting ? "محصول از سبد برداشته شد." : "سبد خرید به‌روز شد.";
        if (deleting) undoButton.focus();
      } catch (e) {
        input.value = fa(Number(input.dataset.saved));
        feedback.textContent = "پاسخ دریافت نشد. پیش از تلاش دوباره، صفحه را بازخوانی کنید و سبد را بررسی کنید.";
      } finally {
        pending = false; basket.setAttribute("aria-busy", "false");
        basket.querySelectorAll("button,input:not([type=hidden])").forEach(node => { node.disabled = false; });
        undoButton.disabled = false; syncQuantityLimits(); guardCheckout();
      }
    };
    basket.addEventListener("submit", event => {
      const form = event.target.closest("[data-basket-update],[data-basket-remove]");
      if (!form) return; event.preventDefault(); send(form, form.hasAttribute("data-basket-remove"));
    });
    basket.addEventListener("click", event => {
      const step = event.target.closest("[data-step]");
      if (!step || pending) return;
      const form = step.closest("form"), input = form.querySelector('[name="quantity"]');
      const value = Number(ascii(input.value));
      const current = Number.isInteger(value) && ascii(input.value).trim() ? value : Number(input.dataset.saved);
      const next = Math.min(99, Math.max(0, current + Number(step.dataset.step)));
      if (next === current) return;
      input.value = fa(next);
      send(form);
    });
    basket.addEventListener("input", guardCheckout);
    basket.addEventListener("change", event => { if (event.target.name === "quantity") send(event.target.closest("form")); });
    undoButton.addEventListener("click", () => { if (undo) send(undo.form, false, undo.quantity); });
    document.addEventListener("click", event => {
      const link = event.target.closest('[data-basket-checkout][aria-disabled="true"]');
      if (link) { event.preventDefault(); feedback.textContent = "ابتدا تعداد محصولات را ثبت کنید و منتظر به‌روزرسانی سبد بمانید."; }
    });
    syncQuantityLimits(); guardCheckout();
    const checkoutBar = document.querySelector(".basket-mobile-checkout");
    new ResizeObserver(() => document.documentElement.style.setProperty("--basket-action-height", `${checkoutBar.getBoundingClientRect().height}px`)).observe(checkoutBar);
  }

  const profileForm = document.querySelector("[data-profile-save]");
  if (profileForm) {
    const name = profileForm.querySelector('[name="display_name"]');
    const initialName = name.value;
    let saving = false;
    const isDirty = () => name.value !== initialName;
    name.addEventListener("input", () => { profileForm.querySelector(".profile-dirty-hint").hidden = !isDirty(); });
    profileForm.addEventListener("submit", () => {
      saving = true;
      const button = profileForm.querySelector('button[type="submit"]');
      button.disabled = true; button.textContent = "در حال ذخیره…";
    });
    window.addEventListener("beforeunload", event => {
      if (isDirty() && !saving) { event.preventDefault(); event.returnValue = ""; }
    });
    const error = profileForm.querySelector(".field-error");
    if (error) { name.setAttribute("aria-invalid", "true"); name.focus(); }
  }

  document.querySelectorAll("[data-product-gallery]").forEach(gallery => {
    const slides = [...gallery.querySelectorAll("[data-gallery-slide]")];
    if (!slides.length) return;
    let index = 0, touchX = null, touchY = null;
    const stage = gallery.querySelector(".gallery-stage");
    const dialog = gallery.querySelector("dialog");
    const select = value => {
      index = (value + slides.length) % slides.length;
      slides.forEach((slide, i) => { slide.hidden = i !== index; });
      gallery.querySelectorAll("[data-gallery-select]").forEach(button => {
        if (Number(button.dataset.gallerySelect) === index) button.setAttribute("aria-current", "true");
        else button.removeAttribute("aria-current");
      });
      const count = gallery.querySelector("[data-gallery-count]");
      if (count) count.textContent = new Intl.NumberFormat("fa-IR").format(index + 1) + " از " + new Intl.NumberFormat("fa-IR").format(slides.length);
    };
    gallery.querySelectorAll("[data-gallery-select]").forEach(button => button.addEventListener("click", () => select(Number(button.dataset.gallerySelect))));
    gallery.querySelector("[data-gallery-prev]")?.addEventListener("click", () => select(index - 1));
    gallery.querySelector("[data-gallery-next]")?.addEventListener("click", () => select(index + 1));
    stage.addEventListener("keydown", event => {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); select(index + (event.key === "ArrowLeft" ? 1 : -1)); }
    });
    stage.addEventListener("touchstart", event => { touchX = event.changedTouches[0].clientX; touchY = event.changedTouches[0].clientY; }, {passive:true});
    stage.addEventListener("touchend", event => {
      if (touchX === null) return;
      const dx = event.changedTouches[0].clientX - touchX, dy = event.changedTouches[0].clientY - touchY;
      if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy)) select(index + (dx > 0 ? 1 : -1));
      touchX = null;
    }, {passive:true});
    let oldOverflow = "";
    slides.forEach(slide => slide.addEventListener("click", () => {
      const image = slides[index].querySelector("img"), expanded = dialog.querySelector("img");
      expanded.src = image.src; expanded.alt = image.alt;
      oldOverflow = document.body.style.overflow; document.body.style.overflow = "hidden";
      dialog.showModal();
    }));
    dialog.querySelector("[data-gallery-close]").addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", event => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener("close", () => { document.body.style.overflow = oldOverflow; slides[index].focus(); });
    select(0);
  });

  // Reveal animation on scroll
  const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
  const targets = document.querySelectorAll("[data-reveal]");

  if (targets.length && "IntersectionObserver" in window && !motionPreference.matches) {
    document.documentElement.classList.add("has-reveal");
    const observer = new IntersectionObserver((entries, activeObserver) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.dataset.revealed = "true";
        activeObserver.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -48px 0px", threshold: 0.12 });

    targets.forEach((target) => observer.observe(target));
  }

  // ==========================================
  // Sidebar + Drawer Filter System
  // ==========================================
  const filterForm = document.getElementById("menu-filters-form");
  let results = document.getElementById("menu-results");
  if (filterForm && results) {
  const input = filterForm.querySelector(".search-text-input");
  const clearBtn = filterForm.querySelector(".search-clear-btn");
  const magnifier = filterForm.querySelector(".search-magnifier");
  const spinner = filterForm.querySelector(".search-spinner");
  const resetBtn = document.getElementById("filter-reset-btn");

  // Drawer elements
  const drawerTrigger = document.getElementById("filter-drawer-trigger");
  const drawer = document.getElementById("filter-drawer");
  const drawerBackdrop = document.getElementById("filter-drawer-backdrop");
  const drawerClose = document.getElementById("filter-drawer-close");
  const drawerApply = document.getElementById("filter-drawer-apply");
  const drawerReset = document.getElementById("filter-drawer-reset");

  let timer, controller, sequence = 0;

  const controls = () => {
    if (clearBtn) clearBtn.style.display = input?.value ? "inline-flex" : "none";
  };

  const hasActiveFilters = () => {
    const fd = new FormData(filterForm);
    return !!(fd.get("category") || fd.get("diet") || fd.get("flavor") || fd.get("ingredient") || input?.value);
  };

  const formURL = () => {
    const url = new URL(filterForm.action, location.href);
    for (const [key, value] of new FormData(filterForm)) {
      if (value) url.searchParams.set(key, value);
    }
    return url;
  };

  const categoryTrack = document.querySelector(".category-track");
  document.querySelectorAll("[data-category-scroll]").forEach(button => button.addEventListener("click", () => {
    categoryTrack?.scrollBy({left: -Number(button.dataset.categoryScroll) * categoryTrack.clientWidth * .75,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth"});
  }));
  categoryTrack?.addEventListener("click", event => {
    const link = event.target.closest("[data-category]");
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    for (const container of [filterForm, drawer].filter(Boolean)) {
      container.querySelectorAll('input[name="category"],input[name="d_category"]').forEach(radio => { radio.checked = radio.value === link.dataset.category; });
    }
    clearTimeout(timer);
    load(formURL());
  });
  const updateResetVisibility = () => {
    const active = hasActiveFilters();
    const category = filterForm.querySelector('input[name="category"]:checked')?.value || "";
    categoryTrack?.querySelectorAll("[data-category]").forEach(link => {
      const on = link.dataset.category === category;
      link.classList.toggle("is-active", on);
      if (on) link.setAttribute("aria-current", "true"); else link.removeAttribute("aria-current");
    });
    if (resetBtn) resetBtn.hidden = !active;
    // Update mobile trigger dot
    const dot = drawerTrigger?.querySelector(".filter-active-dot");
    if (active && !dot && drawerTrigger) {
      const d = document.createElement("span");
      d.className = "filter-active-dot";
      drawerTrigger.append(d);
    } else if (!active && dot) {
      dot.remove();
    }
  };

  const load = async (url, push = true) => {
    controller?.abort();
    controller = new AbortController();
    const current = ++sequence;
    results.setAttribute("aria-busy", "true");
    if (magnifier) magnifier.style.display = "none";
    if (spinner) spinner.style.display = "inline-flex";
    if (mobileMagnifier) mobileMagnifier.style.display = "none";
    if (mobileSpinner) mobileSpinner.style.display = "inline-flex";
    try {
      const response = await fetch(url, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
        signal: controller.signal,
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const html = await response.text();
      if (current !== sequence) return;
      const replacement = new DOMParser().parseFromString(html, "text/html").querySelector("#menu-results");
      if (!replacement) throw new Error("Missing menu results");
      results.replaceWith(replacement);
      results = replacement;
      replacement.querySelectorAll("[data-reveal]").forEach((card) => {
        card.dataset.revealed = "true";
      });
      if (push) history.pushState({}, "", url);
      updateResetVisibility();
    } catch (error) {
      if (error.name !== "AbortError" && current === sequence) location.assign(url);
    } finally {
      if (current === sequence) {
        results.setAttribute("aria-busy", "false");
        if (magnifier) magnifier.style.display = "";
        if (spinner) spinner.style.display = "none";
        if (mobileMagnifier) mobileMagnifier.style.display = "";
        if (mobileSpinner) mobileSpinner.style.display = "none";
      }
    }
  };

  // Radios retain keyboard semantics; activating checked option clears its group.
  for (const container of [filterForm, drawer].filter(Boolean)) {
    let pressedRadio = null, wasChecked = false;
    const remember = event => {
      const radio = event.target.closest(".filter-option")?.querySelector('input[type="radio"]');
      pressedRadio = radio || null;
      wasChecked = !!radio?.checked;
    };
    container.addEventListener("pointerdown", remember);
    container.addEventListener("keydown", event => {
      if (event.key === " " && event.target.matches('input[type="radio"]')) remember(event);
    });
    container.addEventListener("click", event => {
      if (!event.target.matches('input[type="radio"]')) return;
      const radio = event.target;
      if (radio === pressedRadio && wasChecked) {
        // Cancel native activation, then clear after browser restores checked state.
        event.preventDefault();
        setTimeout(() => {
          radio.checked = false;
          radio.dispatchEvent(new Event("change", { bubbles: true }));
        });
      }
      pressedRadio = null;
      wasChecked = false;
    });
  }

  // Sidebar: radio changes trigger AJAX
  filterForm.addEventListener("change", (e) => {
    if (e.target.matches("input[type='radio']")) {
      clearTimeout(timer);
      load(formURL());
    }
  });

  // Reset button
  if (resetBtn) {
    resetBtn.addEventListener("click", (event) => {
      event.preventDefault();
      clearTimeout(timer);
      filterForm.querySelectorAll("input[type=radio]").forEach(r => { r.checked = false; });
      drawer?.querySelectorAll("input[type=radio]").forEach(r => { r.checked = false; });
      input.value = "";
      if (mobileSearch) mobileSearch.value = "";
      mobileControls();
      controls();
      load(new URL(filterForm.action, location.href));
    });
  }

  filterForm.addEventListener("submit", (event) => {
    event.preventDefault();
    clearTimeout(timer);
    load(formURL());
  });

  // Search input
  input?.addEventListener("input", () => controller?.abort());
  if (input) {
    controls();
    input.addEventListener("input", () => {
      if (mobileSearch) mobileSearch.value = input.value;
      mobileControls();
      controls();
      clearTimeout(timer);
      timer = setTimeout(() => load(formURL()), 300);
    });
    input.addEventListener("keydown", (event) => {
      if (event.isComposing) return;
      if (event.key === "Enter") {
        event.preventDefault();
        clearTimeout(timer);
        load(formURL());
        return;
      }
      if (event.key === "Escape" && input.value) {
        event.preventDefault();
        input.value = "";
        if (mobileSearch) mobileSearch.value = "";
        mobileControls();
        controls();
        clearTimeout(timer);
        load(formURL());
      }
    });
    clearBtn?.addEventListener("click", () => {
      input.value = "";
      if (mobileSearch) mobileSearch.value = "";
      mobileControls();
      controls();
      input.focus();
      clearTimeout(timer);
      load(formURL());
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && document.activeElement !== input && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        event.preventDefault();
        const visibleSearch = mobileSearch?.getClientRects().length ? mobileSearch : input;
        visibleSearch.focus();
        visibleSearch.select();
      }
    });
  }

  // popstate
  window.addEventListener("popstate", () => {
    const params = new URLSearchParams(location.search);
    // Restore sidebar radios
    for (const key of ["category", "diet", "flavor", "ingredient"]) {
      const val = params.get(key) || "";
      filterForm.querySelectorAll(`input[name="${key}"]`).forEach((r) => {
        r.checked = r.value === val;
      });
    }
    const qControl = filterForm.elements.namedItem("q");
    if (qControl) qControl.value = params.get("q") || "";
    controls();
    load(location.href, false);
  });

  // ==========================================
  // Mobile Drawer
  // ==========================================
  const openDrawer = () => {
    if (!drawer || !drawerBackdrop) return;
    // Sync drawer radios from sidebar state
    for (const key of ["category", "diet", "flavor", "ingredient"]) {
      const sidebarChecked = filterForm.querySelector(`input[name="${key}"]:checked`);
      const val = sidebarChecked?.value || "";
      drawer.querySelectorAll(`input[name="d_${key}"]`).forEach((r) => {
        r.checked = r.value === val;
      });
    }
    drawerBackdrop.hidden = false;
    requestAnimationFrame(() => {
      drawerBackdrop.classList.add("is-visible");
      drawer.setAttribute("aria-hidden", "false");
    });
    modal(drawer, true, drawerTrigger);
    drawerTrigger.setAttribute("aria-expanded", "true");
  };

  const closeDrawer = () => {
    if (!drawer || !drawerBackdrop) return;
    drawer.setAttribute("aria-hidden", "true");
    drawerBackdrop.classList.remove("is-visible");
    modal(drawer, false, drawerTrigger);
    drawerTrigger?.setAttribute("aria-expanded", "false");
    setTimeout(() => { drawerBackdrop.hidden = true; }, 320);
  };

  window.matchMedia("(min-width: 800px)").addEventListener("change", closeDrawer);
  drawerTrigger?.addEventListener("click", openDrawer);
  drawerClose?.addEventListener("click", closeDrawer);
  drawerBackdrop?.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && drawer?.getAttribute("aria-hidden") === "false") {
      closeDrawer();
    }
  });

  // Apply each selection immediately; keep drawer open for additional choices.
  const applyDrawerFilters = () => {
    for (const key of ["category", "diet", "flavor", "ingredient"]) {
      const drawerChecked = drawer.querySelector(`input[name="d_${key}"]:checked`);
      const val = drawerChecked?.value || "";
      filterForm.querySelectorAll(`input[name="${key}"]`).forEach((r) => {
        r.checked = r.value === val;
      });
      // Uncheck sidebar if nothing selected in drawer
      if (!val) {
        filterForm.querySelectorAll(`input[name="${key}"]`).forEach((r) => { r.checked = false; });
      }
    }
    clearTimeout(timer);
    updateResetVisibility();
    load(formURL());
  };
  drawer?.addEventListener("change", event => {
    if (event.target.matches("input[type=radio]")) applyDrawerFilters();
  });
  drawerApply?.addEventListener("click", closeDrawer);

  // Drawer reset
  drawerReset?.addEventListener("click", (e) => {
    e.preventDefault();
    drawer.querySelectorAll("input[type='radio']").forEach((r) => { r.checked = false; });
    input.value = "";
    if (mobileSearch) mobileSearch.value = "";
    controls();
    mobileControls();
    applyDrawerFilters();
  });
  // ==========================================
  // Mobile search input sync
  // ==========================================
  const mobileSearch = document.getElementById("mobile-search-input");
  const mobileClear = mobileSearch?.closest(".search-input-field")?.querySelector(".search-clear-btn");
  const mobileMagnifier = mobileSearch?.closest(".search-input-field")?.querySelector(".search-magnifier");
  const mobileSpinner = mobileSearch?.closest(".search-input-field")?.querySelector(".search-spinner");

  const mobileControls = () => {
    if (mobileClear) mobileClear.style.display = mobileSearch?.value ? "inline-flex" : "none";
  };

  if (mobileSearch && input) {
    // Sync mobile search to sidebar form's q input
    mobileSearch.addEventListener("input", () => {
      input.value = mobileSearch.value;
      controls();
      mobileControls();
      clearTimeout(timer);
      controller?.abort();
      timer = setTimeout(() => load(formURL()), 300);
    });
    mobileSearch.addEventListener("keydown", (event) => {
      if (event.isComposing) return;
      if (event.key === "Enter") {
        event.preventDefault();
        clearTimeout(timer);
        load(formURL());
        return;
      }
      if (event.key === "Escape" && mobileSearch.value) {
        event.preventDefault();
        mobileSearch.value = "";
        input.value = "";
        if (mobileSearch) mobileSearch.value = "";
        mobileControls();
        controls();
        mobileControls();
        clearTimeout(timer);
        load(formURL());
      }
    });
    mobileClear?.addEventListener("click", () => {
      mobileSearch.value = "";
      input.value = "";
      if (mobileSearch) mobileSearch.value = "";
      mobileControls();
      controls();
      mobileControls();
      mobileSearch.focus();
      clearTimeout(timer);
      load(formURL());
    });
    // Keep them in sync on popstate
    const origPopstate = window.onpopstate;
    window.addEventListener("popstate", () => {
      mobileSearch.value = input.value;
      mobileControls();
    });
    mobileControls();
  }

  document.addEventListener("click", (event) => {
    const reset = event.target.closest("#menu-dynamic-reset-btn");
    if (reset) {
      if (input) input.value = "";
      if (mobileSearch) mobileSearch.value = "";
      controls();
      mobileControls();
      clearTimeout(timer);
      load(formURL());
    }
  });
  }

  // Card click delegation to product details
  document.addEventListener("click", (event) => {
    const card = event.target.closest(".product-item[data-href]");
    if (!card) return;
    if (event.target.closest("button, form, input, a, select, textarea")) return;
    const url = card.dataset.href;
    if (url) {
      if (event.ctrlKey || event.metaKey) {
        window.open(url, "_blank");
      } else {
        window.location.href = url;
      }
    }
  });

  // Dynamic weight selection on product detail
  const weightSelector = document.querySelector("[data-weight-selector]");
  if (weightSelector) {
    const pills = weightSelector.querySelectorAll("[data-weight-pill]");
    const priceWrap = document.querySelector("[data-detail-price-wrap]");
    const numberFormat = new Intl.NumberFormat("fa-IR");
    const setText = (element, value) => {
      if (element && element.textContent !== value) element.textContent = value;
    };

    const updateWeightUI = (radio) => {
      if (!radio?.checked) return;
      pills.forEach((pill) => {
        const input = pill.querySelector('input[type="radio"]');
        pill.classList.toggle("is-active", Boolean(input && input.checked));
      });

      if (priceWrap) {
        const price = Number(radio.dataset.price);
        const original = Number(radio.dataset.originalPrice);
        if (!Number.isFinite(price) || price <= 0) return;
        const percent = Number.isFinite(original) && original > price
          ? Math.round((original - price) * 100 / original)
          : 0;
        setText(priceWrap.querySelector("[data-price-context]"), `قیمت یک بسته · ${radio.dataset.weightLabel}`);
        setText(priceWrap.querySelector(".price-amount bdi") || priceWrap.querySelector(".price-amount"), numberFormat.format(price));

        const discountRow = priceWrap.querySelector(".price-discount-row");
        if (discountRow) {
          setText(discountRow.querySelector(".price-original"), percent > 0 ? numberFormat.format(original) : "");
          setText(discountRow.querySelector(".price-badge"), percent > 0 ? `${numberFormat.format(percent)}٪ تخفیف` : "");
          discountRow.hidden = percent <= 0;
        }
      }
    };

    weightSelector.addEventListener("change", (e) => {
      const radio = e.target.closest('input[type="radio"][name="weight_id"]');
      if (radio) updateWeightUI(radio);
    });
    // Labels and native radios handle pointer and keyboard selection themselves.
    const syncSelectedWeight = () => updateWeightUI(weightSelector.querySelector('input[name="weight_id"]:checked'));
    syncSelectedWeight();
    window.addEventListener("pageshow", syncSelectedWeight);
  }
})();
