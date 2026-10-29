"use strict";
const translations = JSON.parse(document.getElementById("translations")?.textContent || "{}");
const tr = key => translations[key] || key;

/* Language Switcher */
const language = document.getElementById("language");
language?.addEventListener("change", () => {
  const url = new URL(window.location.href);
  url.searchParams.set("lang", language.value);
  window.location.assign(url);
});

/* Delivery Address Hint & Branch Toggle */
const delivery = document.getElementById("delivery");
if (delivery) {
  const keys = {
    "Домашняя доставка": "home_delivery",
    "InPost locker": "inpost",
    "Evri пункт выдачи": "evri",
    "Royal Mail отделение": "royal_mail",
    "Другой": "other_delivery"
  };
  const hint = document.getElementById("addressHint");
  const wrap = document.getElementById("branchWrap");
  const branch = document.getElementById("branch");
  const updateAddress = () => {
    const address = (window.deliveryAddresses || {})[keys[delivery.value]] || "";
    hint.textContent = !delivery.value
      ? ""
      : address
      ? tr("Адрес для выкупа:") + " " + address
      : tr("Адрес ещё не указан. Напишите администратору.");
    hint.hidden = !delivery.value;
    wrap.hidden = delivery.value === "Домашняя доставка";
    branch.required = false;
    if (!branch.required) branch.setCustomValidity("");
  };
  delivery.addEventListener("change", updateAddress);
  updateAddress();
}

/* File Input Display & Drag/Drop Visual Feedback */
document.querySelectorAll(".upload-tile input, .file-button input").forEach(input => {
  const label = input.closest("label");
  const display = document.createElement("span");
  display.className = "selected-file";
  display.textContent = tr("Выбрать файл");
  label.append(display);
  input.addEventListener("change", () => {
    display.textContent = input.files?.[0]?.name || tr("Выбрать файл");
    label.classList.toggle("has-file", Boolean(input.files?.length));
    input.setCustomValidity("");
  });
});

/* Form Validation Localization */
document.querySelectorAll("input, select, textarea").forEach(input => {
  input.addEventListener("invalid", () => {
    input.setCustomValidity("");
    if (input.validity.valueMissing) {
      input.setCustomValidity(
        tr(
          input.type === "checkbox"
            ? "Подтвердите это условие."
            : input.type === "file"
            ? "Прикрепите обязательное фото."
            : "Заполните это поле."
        )
      );
    } else if (input.validity.typeMismatch && input.type === "email") {
      input.setCustomValidity(tr("Введите корректный email."));
    } else if (input.validity.tooShort) {
      input.setCustomValidity(tr("Используйте не менее 8 символов."));
    }
  });
  input.addEventListener("input", () => input.setCustomValidity(""));
  input.addEventListener("change", () => input.setCustomValidity(""));
});

/* Mini Tour Dialog */
const tourSteps = [
  { icon: "🚚", title: "Покупка отправлена", text: "Дождись статуса Shipped, затем добавь скрин покупки и фото вещи.", cls: "road" },
  { icon: "📦 👍", title: "Посылка принята", text: "Администратор отметит получение и приложит фотоотчёт к заявке.", cls: "received" },
  { icon: "📸", title: "Проверь фотоотчёт", text: "В течение двух дней можно запросить возврат или дополнительные фото.", cls: "photos" },
  { icon: "💪", title: "Доставлено!", text: "После отправки появится общий трек-номер. Следи за посылкой в личном кабинете.", cls: "delivered" }
];
const tour = document.getElementById("tour");
if (tour) {
  let step = 0;
  const visual = document.getElementById("tourVisual");
  const previous = document.getElementById("tourPrev");
  const next = document.getElementById("tourNext");
  const paint = () => {
    visual.className = "tour-visual is-" + tourSteps[step].cls;
    const icon = document.createElement("span");
    icon.textContent = tourSteps[step].icon;
    visual.replaceChildren(icon);
    document.getElementById("tourTitle").textContent = tr(tourSteps[step].title);
    document.getElementById("tourText").textContent = tr(tourSteps[step].text);
    document.getElementById("tourCount").textContent = String(step + 1).padStart(2, "0") + " / 04";
    next.textContent = tr(step === 3 ? "Готово ✓" : "Далее ↗");
    previous.disabled = step === 0;
  };
  const close = () => tour.close();
  document.querySelectorAll("[data-tutorial]").forEach(button =>
    button.addEventListener("click", () => {
      step = 0;
      paint();
      tour.showModal();
    })
  );
  document.querySelector("[data-tour-close]")?.addEventListener("click", close);
  tour.addEventListener("click", event => {
    const bounds = tour.getBoundingClientRect();
    if (
      event.target === tour &&
      (event.clientX < bounds.left ||
        event.clientX > bounds.right ||
        event.clientY < bounds.top ||
        event.clientY > bounds.bottom)
    ) {
      close();
    }
  });
  previous.addEventListener("click", () => {
    step = Math.max(0, step - 1);
    paint();
  });
  next.addEventListener("click", () => {
    if (step === tourSteps.length - 1) close();
    else {
      step += 1;
      paint();
    }
  });
  paint();
}

/* ==========================================================================
   HYPER-DYNAMIC CHOREOGRAPHY, 3D TILT, MAGNETIC BUTTONS & PAGE TRANSITIONS
   ========================================================================== */

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* 1. Scroll Progress Bar & Floating Topbar State */
const scrollProgress = document.getElementById("scrollProgress");
const topbar = document.getElementById("topbar") || document.querySelector(".topbar");
const syncScroll = () => {
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const docHeight = document.documentElement.scrollHeight - window.innerHeight;
  if (scrollProgress) {
    const ratio = docHeight > 0 ? Math.min(1, Math.max(0, scrollTop / docHeight)) : 0;
    scrollProgress.style.transform = `scaleX(${ratio})`;
  }
  if (topbar) {
    topbar.classList.toggle("is-scrolled", scrollTop > 18);
  }
};
window.addEventListener("scroll", syncScroll, { passive: true });
syncScroll();

if (!reducedMotion) {
  /* 2. Staggered Scroll Reveal Choreography */
  if ("IntersectionObserver" in window) {
    const reveal = new IntersectionObserver(
      entries =>
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            reveal.unobserve(entry.target);
          }
        }),
      { threshold: 0.08, rootMargin: "0px 0px -30px 0px" }
    );
    document.documentElement.classList.add("js-motion");
    const revealTargets = document.querySelectorAll(
      ".steps article, .price-card, .order-card, .contact-card, .review-box, .cta, .admin-section, .address-card, .profile-stats > div, .stats > div, .form-card, .payment-summary"
    );
    revealTargets.forEach((element, index) => {
      element.classList.add("reveal");
      element.style.setProperty("--reveal-delay", (index % 4) * 75 + "ms");
      reveal.observe(element);
    });
  }

  /* 3. Ambient Cursor Glow Follower */
  const cursorGlow = document.getElementById("cursorGlow");
  if (cursorGlow && window.matchMedia("(pointer: fine)").matches) {
    let mouseX = -1000;
    let mouseY = -1000;
    let rafId = 0;
    window.addEventListener(
      "pointermove",
      e => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            cursorGlow.style.setProperty("--cursor-x", `${mouseX}px`);
            cursorGlow.style.setProperty("--cursor-y", `${mouseY}px`);
            rafId = 0;
          });
        }
      },
      { passive: true }
    );
  }

  /* 4. Interactive 3D Card Tilt & Radial Spotlight Tracking */
  if (window.matchMedia("(pointer: fine)").matches) {
    const tiltCards = document.querySelectorAll(
      ".route-card, .steps article, .price-card, .contact-card, .order-card, .address-card, .form-card"
    );
    tiltCards.forEach(card => {
      const isSubtle = card.classList.contains("form-card") || card.classList.contains("order-card");
      const maxDeg = isSubtle ? 2.2 : 5.5;
      card.addEventListener("pointermove", e => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const px = x / rect.width - 0.5;
        const py = y / rect.height - 0.5;
        card.style.setProperty("--spot-x", `${Math.round((x / rect.width) * 100)}%`);
        card.style.setProperty("--spot-y", `${Math.round((y / rect.height) * 100)}%`);
        card.style.setProperty("--rx", `${(-py * maxDeg).toFixed(2)}deg`);
        card.style.setProperty("--ry", `${(px * maxDeg).toFixed(2)}deg`);
      });
      card.addEventListener("pointerleave", () => {
        card.style.setProperty("--rx", "0deg");
        card.style.setProperty("--ry", "0deg");
      });
    });

    /* 5. Magnetic Button Micro-Pull */
    document.querySelectorAll(".button.primary, .nav-cta").forEach(btn => {
      btn.addEventListener("pointermove", e => {
        const rect = btn.getBoundingClientRect();
        const dx = (e.clientX - (rect.left + rect.width / 2)) * 0.18;
        const dy = (e.clientY - (rect.top + rect.height / 2)) * 0.22;
        btn.style.setProperty("--mag-x", `${dx.toFixed(1)}px`);
        btn.style.setProperty("--mag-y", `${dy.toFixed(1)}px`);
      });
      btn.addEventListener("pointerleave", () => {
        btn.style.setProperty("--mag-x", "0px");
        btn.style.setProperty("--mag-y", "0px");
      });
    });
  }

  /* 6. Smooth Page Navigation Transitions */
  document.addEventListener("click", e => {
    const link = e.target.closest("a[href]");
    if (!link) return;
    const href = link.getAttribute("href");
    if (
      !href ||
      href.startsWith("#") ||
      href.startsWith("javascript:") ||
      link.target === "_blank" ||
      link.hasAttribute("download") ||
      e.metaKey ||
      e.ctrlKey ||
      e.shiftKey ||
      e.altKey
    ) {
      return;
    }
    try {
      const targetUrl = new URL(href, window.location.origin);
      if (targetUrl.origin !== window.location.origin) return;
      if (targetUrl.pathname === window.location.pathname && targetUrl.search === window.location.search && targetUrl.hash) {
        return;
      }
      if (!document.startViewTransition) {
        e.preventDefault();
        document.body.classList.add("page-leaving");
        setTimeout(() => {
          window.location.assign(targetUrl.href);
        }, 190);
      }
    } catch {
      /* Let default browser navigation proceed */
    }
  });
}
