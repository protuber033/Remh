
async function requestQuote(form, serviceId) {
  const formData = new FormData(form);
  const answers = {};
  for (const [key, value] of formData.entries()) {
    if (!value) continue;
    const field = form.querySelector(`[name="${key}"]`);
    if (field && field.dataset.inputType === 'number') {
      answers[key] = Number(value);
    } else {
      answers[key] = value;
    }
  }
  const postcode = form.querySelector('[name="postcode"]').value;
  const response = await fetch('/api/quote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ service_id: serviceId, answers, postcode })
  });
  if (!response.ok) {
    throw new Error('Serverfout');
  }
  return response.json();
}

function hydrateConfigurator() {
  const form = document.querySelector('[data-config-form]');
  if (!form) return;
  const serviceId = form.dataset.serviceId;
  const summary = document.querySelector('[data-summary]');
  const breakdown = document.querySelector('[data-breakdown]');
  const message = document.querySelector('[data-message]');

  async function update() {
    try {
      const quote = await requestQuote(form, serviceId);
      summary.querySelector('[data-total]').textContent = `€ ${quote.total.toLocaleString('nl-NL')}`;
      breakdown.innerHTML = '';
      quote.breakdown.forEach(row => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${row.label}</span><strong>€ ${Number(row.amount).toLocaleString('nl-NL')}</strong>`;
        breakdown.appendChild(li);
      });
      message.textContent = quote.message;
    } catch (err) {
      message.textContent = err.message;
    }
  }

  form.addEventListener('input', () => {
    clearTimeout(form._debounce);
    form._debounce = setTimeout(update, 300);
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    update();
  });
  update();
}

document.addEventListener('DOMContentLoaded', hydrateConfigurator);
