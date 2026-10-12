(() => {
  const digitMap = "۰۱۲۳۴۵۶۷۸۹";
  const toFa = (num) => String(num).replace(/[0-9]/g, (d) => digitMap[Number(d)]);
  const normalize = (value) => (value || "")
    .replace(/[۰-۹]/g, (digit) => String(digitMap.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)))
    .replace(/[^0-9]/g, "");

  // ==========================================
  // Step 0: Phone validation & auto-enable
  // ==========================================
  const phoneForm = document.querySelector("#auth-phone-form");
  if (phoneForm) {
    const phoneInput = phoneForm.querySelector("#auth-phone");
    const submitBtn = phoneForm.querySelector("#auth-phone-submit");

    const validatePhone = () => {
      if (!phoneInput || !submitBtn) return;
      const clean = normalize(phoneInput.value);
      // Iranian mobile: 11 digits starting with 09 (or 10 digits starting with 9)
      const isValid = /^0?9\d{9}$/.test(clean);
      submitBtn.disabled = !isValid;
    };

    if (phoneInput && submitBtn) {
      phoneInput.addEventListener("input", validatePhone);
      validatePhone();
    }
  }

  // ==========================================
  // Step 1: OTP Fields, Auto-submit & Timer
  // ==========================================
  const group = document.querySelector("[data-otp-field]");
  const form = document.querySelector("[data-otp-form]");
  const backing = form?.elements.namedItem("code");
  const inputs = [...(group?.querySelectorAll("[data-otp-slot]") || [])];

  if (form && group && backing && inputs.length === 6) {
    const digits = Array.from({ length: inputs.length }, (_, index) => normalize(backing.value)[index] || "");
    const error = form.querySelector("[data-otp-error]");
    const serverError = form.querySelector("#otp-server-error");
    const field = group.closest(".form-field");

    const clearErrors = () => {
      field?.classList.remove("has-error");
      group.removeAttribute("aria-invalid");
      group.removeAttribute("data-phase");
      if (error) error.hidden = true;
      if (serverError) serverError.hidden = true;
    };

    const triggerDigitAnimation = (input) => {
      input.classList.remove("has-digit");
      void input.offsetWidth; // trigger reflow
      input.classList.add("has-digit");
    };

    const setReject = () => {
      field?.classList.add("has-error");
      group.setAttribute("aria-invalid", "true");
      group.setAttribute("data-phase", "no");
      group.style.animation = "none";
      void group.offsetWidth; // trigger reflow
      group.style.animation = "";
    };

    const render = () => {
      inputs.forEach((input, index) => {
        const prevVal = input.value;
        const newVal = digits[index] ? digitMap[Number(digits[index])] : "";
        input.value = newVal;
        input.dataset.filled = String(Boolean(digits[index]));
        if (newVal && newVal !== prevVal) {
          triggerDigitAnimation(input);
        } else if (!newVal) {
          input.classList.remove("has-digit");
        }
      });
      backing.value = digits.join("");
    };

    const focusAt = (index) => {
      const input = inputs[Math.min(Math.max(index, 0), inputs.length - 1)];
      input?.focus();
      input?.select();
    };

    let isSubmitting = false;
    const submitIfComplete = () => {
      if (digits.every(Boolean) && !isSubmitting) {
        isSubmitting = true;
        backing.value = digits.join("");
        group.setAttribute("data-phase", "ok");
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
          submitBtn.classList.add("is-loading");
          submitBtn.textContent = "در حال بررسی و ورود…";
        }
        setTimeout(() => {
          form.submit();
        }, 180);
      }
    };

    const fill = (index, value) => {
      const clean = normalize(value);
      if (!clean) return;
      clearErrors();
      const start = clean.length >= inputs.length ? 0 : index;
      for (let offset = 0; offset < clean.length && start + offset < inputs.length; offset += 1) {
        digits[start + offset] = clean[offset];
      }
      render();
      if (digits.every(Boolean)) {
        submitIfComplete();
      } else {
        focusAt(start + clean.length);
      }
    };

    backing.type = "hidden";
    backing.autocomplete = "off";
    group.hidden = false;
    render();

    if (serverError || field?.classList.contains("has-error")) {
      setReject();
    }

    // Auto-focus first empty slot
    const firstEmpty = digits.findIndex((digit) => !digit);
    focusAt(firstEmpty === -1 ? 0 : firstEmpty);

    inputs.forEach((input, index) => {
      input.addEventListener("focus", () => input.select());
      input.addEventListener("pointerdown", (event) => {
        const emptySlot = digits.findIndex((digit) => !digit);
        if (emptySlot !== -1 && index > emptySlot) {
          event.preventDefault();
          focusAt(emptySlot);
        }
      });
      input.addEventListener("input", () => {
        const value = normalize(input.value);
        clearErrors();
        if (value.length > 1) {
          const typed = value.length === 2 && value[0] === digits[index] ? value[1] : null;
          if (!typed) return fill(index, value);
          digits[index] = typed;
        } else {
          digits[index] = value;
        }
        render();
        if (digits[index] && index < inputs.length - 1) {
          focusAt(index + 1);
        }
        if (digits.every(Boolean)) {
          submitIfComplete();
        }
      });
      input.addEventListener("paste", (event) => {
        event.preventDefault();
        fill(index, event.clipboardData.getData("text"));
      });
      input.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          focusAt(index + (event.key === "ArrowLeft" ? -1 : 1));
        } else if (event.key === "Home" || event.key === "End") {
          event.preventDefault();
          focusAt(event.key === "Home" ? 0 : inputs.length - 1);
        } else if (event.key === "Backspace" || event.key === "Delete") {
          event.preventDefault();
          clearErrors();
          const target = event.key === "Backspace" && !digits[index] ? Math.max(0, index - 1) : index;
          digits[target] = "";
          render();
          focusAt(target);
        }
      });
    });

    form.addEventListener("submit", (event) => {
      if (backing.value.length === 6 && digits.every(Boolean)) {
        group.setAttribute("data-phase", "ok");
        return;
      }
      event.preventDefault();
      setReject();
      if (error) error.hidden = false;
      focusAt(Math.max(0, digits.findIndex((digit) => !digit)));
    });

    // 90s countdown timer
    const timerSpan = document.querySelector("#resend-timer");
    const resendBtn = document.querySelector("#resend-btn");
    let left = 90;

    const tick = () => {
      if (!timerSpan || !resendBtn) return;
      if (left > 0) {
        timerSpan.textContent = `ارسال دوباره تا ${toFa(left)} ثانیه`;
        timerSpan.style.display = "inline";
        resendBtn.style.display = "none";
        left -= 1;
        setTimeout(tick, 1000);
      } else {
        timerSpan.style.display = "none";
        resendBtn.style.display = "inline";
      }
    };
    tick();
  }
})();
