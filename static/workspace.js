/* Progressive enhancements: all payment/order actions still work without JS. */
"use strict";
(() => {
  const toolbar = document.querySelector('[data-filter-toolbar]');
  if (toolbar) {
    const cards = [...document.querySelectorAll('[data-parcel-card]')];
    const input = toolbar.querySelector('[data-parcel-search]');
    const chips = [...toolbar.querySelectorAll('[data-parcel-filter]')];
    let filter = 'all';
    const apply = () => {
      const needle = input.value.trim().toLocaleLowerCase();
      let count = 0;
      cards.forEach(card => {
        const state = card.dataset.status;
        const matches = filter === 'all' || (filter === 'payment' && card.dataset.unpaid === '1') ||
          (filter === 'transit' && state === 'Отправлено') ||
          (filter === 'warehouse' && ['Одержано', 'Фотоотчёт готов', 'К отправке'].includes(state));
        card.hidden = !(matches && card.dataset.search.toLocaleLowerCase().includes(needle));
        if (!card.hidden) count++;
      });
      chips.forEach(chip => chip.setAttribute('aria-pressed', String(chip.dataset.parcelFilter === filter)));
      document.querySelector('[data-filter-empty]').hidden = count > 0;
      toolbar.querySelector('[data-result-count]').textContent = `${count} / ${cards.length}`;
    };
    input.addEventListener('input', apply);
    chips.forEach(chip => chip.addEventListener('click', () => {filter = chip.dataset.parcelFilter; apply();}));
    document.querySelector('[data-filter-reset]').addEventListener('click', () => {input.value = ''; filter = 'all'; apply(); input.focus();});
    apply();
  }

  document.querySelectorAll('[data-local-time]').forEach(node => {
    const date = new Date(node.getAttribute('datetime'));
    if (!Number.isNaN(date.getTime())) node.textContent = new Intl.DateTimeFormat(document.documentElement.lang, {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
    }).format(date);
  });

  document.querySelectorAll('input[type=password]').forEach(input => {
    input.autocomplete = location.pathname === '/register' ? 'new-password' : 'current-password';
    const wrap = document.createElement('span'); wrap.className = 'password-field';
    input.before(wrap); wrap.append(input);
    const button = document.createElement('button');button.type = 'button';button.className = 'password-toggle';
    button.textContent = tr('ux.show');button.setAttribute('aria-pressed', 'false');
    button.addEventListener('click', () => {
      const show = input.type === 'password';input.type = show ? 'text' : 'password';
      button.textContent = tr(show ? 'ux.hide' : 'ux.show');button.setAttribute('aria-pressed', String(show));
    });wrap.append(button);
  });
  document.querySelectorAll('input[type=email]').forEach(input => input.autocomplete = 'email');

  const form = document.getElementById('orderForm');
  if (form) {
    const product = form.querySelector('[name=product_type]');
    const item = form.querySelector('[name=item]');
    const summary = () => {
      const option = product.selectedOptions[0];
      document.getElementById('summaryPrice').textContent = option?.dataset.price ? `${option.dataset.price} ₴` : '—';
      document.getElementById('summaryCategory').textContent = option?.value ? option.textContent : '';
      document.getElementById('summaryItem').textContent = item.value.trim() || tr('ux.summary_hint');
    };
    product.addEventListener('change', summary);item.addEventListener('input', summary);summary();
  }

  // Enforce the per-file cap before upload; server validation remains authoritative.
  document.querySelectorAll('input[type=file]').forEach(input => {
    const validate = () => {
      const large = [...(input.files || [])].some(file => file.size > 12 * 1024 * 1024);
      if (large) input.setCustomValidity(tr('ux.file_large'));
      return !large;
    };
    input.addEventListener('change', validate);
    input.addEventListener('invalid', validate);
    input.form?.addEventListener('submit', event => {
      if (!validate()) {event.preventDefault();input.reportValidity();}
    });
  });

  const unlock = () => document.querySelectorAll('form[data-submitting]').forEach(form => {
    delete form.dataset.submitting;form.removeAttribute('aria-busy');
    form.querySelectorAll('[data-submit-label]').forEach(button => {
      button.disabled = false;button.textContent = button.dataset.submitLabel;delete button.dataset.submitLabel;
    });
  });
  document.querySelectorAll('form[method=post], form[method=POST]').forEach(form => {
    if (form.classList.contains('chat-compose')) return;
    form.addEventListener('submit', event => {
      if (event.defaultPrevented) return;
      if (form.dataset.submitting) {event.preventDefault();return;}
      form.dataset.submitting = '1';form.setAttribute('aria-busy', 'true');
      // Named submit buttons must keep their submitted value.
      form.querySelectorAll('button:not([type=button]):not([name])').forEach(button => {
        button.dataset.submitLabel = button.textContent;button.textContent = tr('ux.sending');button.disabled = true;
      });
      window.setTimeout(unlock, 20000);
    });
  });
  window.addEventListener('pageshow', unlock);
})();
