"use strict";
const translations = JSON.parse(document.getElementById("translations")?.textContent || "{}");
const tr = key => translations[key] || key;
const language = document.getElementById("language");
language?.addEventListener("change", () => {
  const url = new URL(window.location.href);
  url.searchParams.set("lang", language.value);
  window.location.assign(url);
});
const delivery = document.getElementById("delivery");
if (delivery) {
  const keys = {"Домашняя доставка":"home_delivery", "InPost locker":"inpost", "Evri пункт выдачи":"evri", "Royal Mail отделение":"royal_mail", "Другой":"other_delivery"};
  const hint = document.getElementById("addressHint");
  const wrap = document.getElementById("branchWrap");
  const branch = document.getElementById("branch");
  const updateAddress = () => {
    const address = (window.deliveryAddresses || {})[keys[delivery.value]] || "";
    hint.textContent = !delivery.value ? "" : address
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
document.querySelectorAll("input, select, textarea").forEach(input => {
  input.addEventListener("invalid", () => {
    input.setCustomValidity("");
    if (input.validity.valueMissing) {
      input.setCustomValidity(tr(input.type === "checkbox" ? "Подтвердите это условие."
        : input.type === "file" ? "Прикрепите обязательное фото." : "Заполните это поле."));
    } else if (input.validity.typeMismatch && input.type === "email") {
      input.setCustomValidity(tr("Введите корректный email."));
    } else if (input.validity.tooShort) {
      input.setCustomValidity(tr("Используйте не менее 8 символов."));
    }
  });
  input.addEventListener("input", () => input.setCustomValidity(""));
  input.addEventListener("change", () => input.setCustomValidity(""));
});
const tourSteps = [
  {icon: "🚚", title: "Покупка отправлена", text: "Дождись статуса Shipped, затем добавь скрин покупки и фото вещи.", cls: "road"},
  {icon: "📦 👍", title: "Посылка принята", text: "Администратор отметит получение и приложит фотоотчёт к заявке.", cls: "received"},
  {icon: "📸", title: "Проверь фотоотчёт", text: "В течение двух дней можно запросить возврат или дополнительные фото.", cls: "photos"},
  {icon: "💪", title: "Доставлено!", text: "После отправки появится общий трек-номер. Следи за посылкой в личном кабинете.", cls: "delivered"}
];
const tour = document.getElementById("tour");
if (tour) {
  let step = 0;
  const visual = document.getElementById("tourVisual");
  const previous = document.getElementById("tourPrev");
  const next = document.getElementById("tourNext");
  const paint = () => {
    visual.className = "tour-visual is-" + tourSteps[step].cls;
    const icon = document.createElement("span"); icon.textContent = tourSteps[step].icon; visual.replaceChildren(icon);
    document.getElementById("tourTitle").textContent = tr(tourSteps[step].title);
    document.getElementById("tourText").textContent = tr(tourSteps[step].text);
    document.getElementById("tourCount").textContent = String(step + 1).padStart(2, "0") + " / 04";
    next.textContent = tr(step === 3 ? "Готово ✓" : "Далее ↗");
    previous.disabled = step === 0;
  };
  const close = () => tour.close();
  document.querySelectorAll("[data-tutorial]").forEach(button => button.addEventListener("click", () => {
    step = 0;
    paint();
    tour.showModal();
  }));
  document.querySelector("[data-tour-close]").addEventListener("click", close);
  tour.addEventListener("click", event => {
    const bounds = tour.getBoundingClientRect();
    if (event.target === tour && (event.clientX < bounds.left || event.clientX > bounds.right ||
      event.clientY < bounds.top || event.clientY > bounds.bottom)) close();
  });
  previous.addEventListener("click", () => { step = Math.max(0, step - 1); paint(); });
  next.addEventListener("click", () => {
    if (step === tourSteps.length - 1) close();
    else { step += 1; paint(); }
  });
  paint();
}
if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  const reveal = new IntersectionObserver(entries => entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add("visible");
      reveal.unobserve(entry.target);
    }
  }), {threshold: 0.08});
  document.documentElement.classList.add("js-motion");
  document.querySelectorAll(".steps article, .order-card, .contact-card, .review-box, .cta, .admin-section").forEach((element, index) => {
    element.classList.add("reveal");
    element.style.setProperty("--reveal-delay", (index % 3) * 70 + "ms");
    reveal.observe(element);
  });
}