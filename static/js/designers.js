(() => {
  // Секция работает независимо от остального магазина и не создаёт дубликатов preview.
  const section = document.querySelector("#designers");
  if (!section) return;

  const preview = section.querySelector(".brand-preview");
  const rows = [...section.querySelectorAll(".designer-row")];
  const mobile = matchMedia("(max-width: 700px), (hover: none)");
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  let active = null;
  let currentX = 0,
    currentY = 0,
    targetX = 0,
    targetY = 0;
  let animationFrame = 0;

  function populate(row) {
    // data-* приходит из Jinja и меняет содержимое одного общего окна.
    preview.querySelector("strong").textContent = row.dataset.name;
    preview.querySelector(".brand-preview-description").textContent =
      row.dataset.description;
    preview.querySelector(".brand-preview-current").textContent = row
      .querySelector(".designer-number")
      .textContent.trim()
      .slice(0, 2);
    preview.querySelector(".brand-preview-link").href = row.href;
  }

  function place(x, y) {
    // Ограничиваем окно viewport, чтобы оно не обрезалось у краёв экрана.
    const rect = preview.getBoundingClientRect();
    const width = rect.width || 290;
    const height = rect.height || 240;
    targetX = Math.max(12, Math.min(x + 26, innerWidth - width - 12));
    targetY = Math.max(12, Math.min(y + 18, innerHeight - height - 12));
    if (reducedMotion.matches) {
      currentX = targetX;
      currentY = targetY;
      preview.style.setProperty("--preview-x", `${currentX}px`);
      preview.style.setProperty("--preview-y", `${currentY}px`);
    }
  }

  function follow() {
    // Lerp .14 создаёт тяжёлое, спокойное движение вслед за курсором.
    if (mobile.matches || !active || reducedMotion.matches) {
      animationFrame = 0;
      return;
    }
    currentX += (targetX - currentX) * 0.14;
    currentY += (targetY - currentY) * 0.14;
    preview.style.setProperty("--preview-x", `${currentX}px`);
    preview.style.setProperty("--preview-y", `${currentY}px`);
    animationFrame = requestAnimationFrame(follow);
  }

  function show(row, x, y) {
    if (active && active !== row) active.classList.remove("is-active");
    active = row;
    row.classList.add("is-active");
    populate(row);
    if (mobile.matches) {
      row.after(preview); // Перемещаем существующее окно, но не создаём новое.
      preview.setAttribute("aria-hidden", "false");
    } else {
      place(x, y);
      if (!animationFrame && !reducedMotion.matches)
        animationFrame = requestAnimationFrame(follow);
    }
    preview.classList.add("is-visible");
  }

  function hide() {
    if (active) active.classList.remove("is-active");
    active = null;
    preview.classList.remove("is-visible");
    preview.setAttribute("aria-hidden", "true");
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = 0;
  }

  rows.forEach((row) => {
    row.addEventListener("pointerenter", (event) => {
      if (!mobile.matches && event.pointerType !== "touch")
        show(row, event.clientX, event.clientY);
    });
    row.addEventListener("pointermove", (event) => {
      if (!mobile.matches && active === row)
        place(event.clientX, event.clientY);
    });
    row.addEventListener("pointerleave", () => {
      if (!mobile.matches && active === row && !row.matches(":focus-visible"))
        hide();
    });
    row.addEventListener("focus", () => {
      if (!mobile.matches) {
        const rect = row.getBoundingClientRect();
        show(row, rect.left + rect.width * 0.55, rect.top + rect.height * 0.5);
      }
    });
    row.addEventListener("blur", () => {
      if (!mobile.matches && active === row) hide();
    });
    row.addEventListener("click", (event) => {
      if (!mobile.matches) return;
      if (active !== row) {
        event.preventDefault();
        show(row);
      } // Повторный tap или ссылка внутри окна открывает страницу бренда.
    });
  });

  document.addEventListener("pointerdown", (event) => {
    if (
      mobile.matches &&
      active &&
      !event.target.closest(".designer-row, .brand-preview")
    )
      hide();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && active) hide();
  });
  mobile.addEventListener("change", () => {
    hide();
    section.append(preview);
  });
})();
