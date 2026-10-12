(function () {
  "use strict";

  function initFlavorWidget(widget) {
    if (widget.dataset.initialized) return;
    widget.dataset.initialized = "true";

    const backingInput = widget.querySelector(".flavor-tags-backing");
    const container = widget.querySelector(".flavor-tags-container");
    const textInput = widget.querySelector(".flavor-tags-input");
    if (!backingInput || !container || !textInput) return;

    let tags = [];

    function parseTags(raw) {
      if (!raw) return [];
      return String(raw)
        .replace(/،/g, ",")
        .split(",")
        .map(function (t) {
          return t.trim();
        })
        .filter(Boolean);
    }

    function syncToBacking() {
      backingInput.value = tags.join("، ");
    }

    function renderTags() {
      container.innerHTML = "";
      tags.forEach(function (tag, index) {
        const chip = document.createElement("span");
        chip.className = "flavor-chip";
        chip.textContent = tag;

        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.className = "flavor-chip-remove";
        removeBtn.innerHTML = "&times;";
        removeBtn.setAttribute("aria-label", "حذف " + tag);
        removeBtn.addEventListener("click", function (e) {
          e.preventDefault();
          tags.splice(index, 1);
          syncToBacking();
          renderTags();
          textInput.focus();
        });

        chip.appendChild(removeBtn);
        container.appendChild(chip);
      });
    }

    function addTag(raw) {
      const parts = parseTags(raw);
      let changed = false;
      parts.forEach(function (p) {
        if (!tags.includes(p)) {
          tags.push(p);
          changed = true;
        }
      });
      if (changed) {
        syncToBacking();
        renderTags();
      }
      textInput.value = "";
    }

    // Initial tags from backing input value
    tags = parseTags(backingInput.value);
    renderTags();

    textInput.addEventListener("keydown", function (e) {
      if (e.key === "Tab" || e.key === "Enter" || e.key === "," || e.key === "،") {
        const val = textInput.value.trim();
        if (val) {
          e.preventDefault();
          addTag(val);
        } else if (e.key === "Enter") {
          e.preventDefault();
        }
      } else if (e.key === "Backspace" && textInput.value === "" && tags.length > 0) {
        e.preventDefault();
        tags.pop();
        syncToBacking();
        renderTags();
      }
    });

    textInput.addEventListener("blur", function () {
      const val = textInput.value.trim();
      if (val) {
        addTag(val);
      }
    });
  }

  function setup() {
    document.querySelectorAll("[data-flavor-tags-root]").forEach(initFlavorWidget);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setup);
  } else {
    setup();
  }
})();
