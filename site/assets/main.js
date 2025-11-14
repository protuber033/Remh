const formatter = new Intl.NumberFormat('nl-NL', {
  style: 'currency',
  currency: 'EUR',
  minimumFractionDigits: 0,
});

const defaults = {
  regionMultiplier: 1,
  workloadFactor: 1,
  rushFactor: 1,
  discount: 0,
};

const isHttpContext = typeof window !== 'undefined' && window.location.protocol.startsWith('http');

function summarize(state, config) {
  return config.summaryFields
    .filter((field) => state[field.id])
    .map((field) => `${field.label}: ${state[field.id]}`);
}

function setSummaryStatus(element, message, variant = 'muted') {
  if (!element) return;
  element.textContent = message ?? '';
  if (variant) {
    element.dataset.variant = variant;
  }
}

function renderSummaryList(container, details, breakdown = []) {
  if (!container) return;
  const detailMarkup = details.map((item) => `<li>${item}</li>`).join('');
  const breakdownMarkup = breakdown
    .map(
      (item) => `
        <li class="summary-breakdown" data-breakdown>
          <span>${item.label}</span>
          <strong>${formatter.format(item.amount)}</strong>
        </li>`
    )
    .join('');
  container.innerHTML = detailMarkup + breakdownMarkup;
}

function hydrateTimeline(container, timeline) {
  if (!container) return;
  container.innerHTML = timeline
    .map((item) => `<li><strong>${item.title}</strong><span>${item.copy}</span></li>`)
    .join('');
}

function hydrateFaq(container, faqs) {
  if (!container) return;
  container.innerHTML = faqs
    .map(
      (faq) => `
      <article class="faq-item">
        <h4>${faq.question}</h4>
        <p>${faq.answer}</p>
      </article>`
    )
    .join('');
}

function stepMarkup(step, values) {
  const controls = step.fields
    .map((field) => {
      const value = values[field.id] ?? field.default ?? '';
      if (field.type === 'select') {
        return `
          <div class="form-field">
            <label for="${field.id}">${field.label}</label>
            <select id="${field.id}" name="${field.id}" ${field.required ? 'required' : ''}>
              ${field.options
                .map(
                  (opt) => `<option value="${opt.value}" ${opt.value === value ? 'selected' : ''}>${opt.label}</option>`
                )
                .join('')}
            </select>
            ${field.help ? `<small>${field.help}</small>` : ''}
          </div>`;
      }

      if (field.type === 'textarea') {
        return `
          <div class="form-field">
            <label for="${field.id}">${field.label}</label>
            <textarea id="${field.id}" name="${field.id}" rows="4">${value}</textarea>
          </div>`;
      }

      return `
        <div class="form-field">
          <label for="${field.id}">${field.label}</label>
          <input
            id="${field.id}"
            name="${field.id}"
            type="${field.type ?? 'text'}"
            value="${value}"
            ${field.min ? `min="${field.min}"` : ''}
            ${field.max ? `max="${field.max}"` : ''}
            ${field.step ? `step="${field.step}"` : ''}
            ${field.required ? 'required' : ''}
          />
          ${field.help ? `<small>${field.help}</small>` : ''}
        </div>`;
    })
    .join('');

  return `
    <section class="step" data-step-id="${step.id}">
      <h3>${step.title}</h3>
      <p>${step.description}</p>
      ${controls}
    </section>`;
}

function attachAssistant(container, config) {
  if (!container) return;
  container.innerHTML = `
    <div class="ai-pill">🤖 AI-assistent</div>
    <h3>${config.assistant.title}</h3>
    <p>${config.assistant.copy}</p>
    <button class="button secondary" data-assistant-action>Bekijk voorbeeldvragen</button>
    <blockquote>${config.assistant.example}</blockquote>
  `;
  const button = container.querySelector('[data-assistant-action]');
  button?.addEventListener('click', () => {
    alert('AI-antwoord:\n' + config.assistant.example);
  });
}

export function bootstrapConfigurator(config) {
  const state = { ...defaults, ...config.defaults };
  config.steps?.forEach((step) => {
    step.fields?.forEach((field) => {
      if (state[field.id] === undefined && field.default !== undefined) {
        state[field.id] = field.default;
      }
    });
  });
  const stepContainer = document.querySelector('[data-stepper]');
  const summaryList = document.querySelector('[data-summary-list]');
  const summaryTotal = document.querySelector('[data-summary-total]');
  const summaryStatus = document.querySelector('[data-summary-status]');
  const notice = document.querySelector('[data-notice]');
  const timeline = document.querySelector('[data-timeline]');
  const faq = document.querySelector('[data-faq]');
  const assistant = document.querySelector('[data-assistant]');
  const stepNavigation = document.querySelector('[data-step-navigation]');

  let currentIndex = 0;
  let baseNotice = '';
  let lastQuoteRequest = 0;

  const requestQuote = async () => {
    if (!config.serviceId) {
      return { total: 0, message: 'Voeg een serviceId toe voor de Python-prijsengine.' };
    }
    if (!isHttpContext) {
      return { total: 0, message: 'Open de site via "python server.py" voor live prijzen.' };
    }
    const response = await fetch('/api/quote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ service: config.serviceId, payload: state }),
    });
    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || 'Onbekende fout tijdens berekening');
    }
    return response.json();
  };

  const render = () => {
    if (!stepContainer) return;
    stepContainer.innerHTML = config.steps
      .map((step, index) => (index === currentIndex ? stepMarkup(step, state) : ''))
      .join('');
    const currentStep = config.steps[currentIndex];
    stepNavigation.querySelector('[data-prev]').disabled = currentIndex === 0;
    stepNavigation.querySelector('[data-next]').textContent =
      currentIndex === config.steps.length - 1 ? 'Opslaan' : 'Volgende';
    baseNotice = currentStep.notice ?? config.notice ?? '';
    if (notice) notice.textContent = baseNotice;
  };

  const updateStateFromInputs = () => {
    const inputs = stepContainer.querySelectorAll('input, select, textarea');
    inputs.forEach((input) => {
      state[input.name] = input.type === 'number' ? Number(input.value) : input.value;
    });
  };

  const updateSummary = async () => {
    const details = summarize(state, config);
    renderSummaryList(summaryList, details);
    const requestId = Date.now();
    lastQuoteRequest = requestId;
    summaryTotal.textContent = '—';
    setSummaryStatus(summaryStatus, 'Prijs wordt berekend…');
    try {
      const quote = await requestQuote();
      if (requestId !== lastQuoteRequest) return;
      summaryTotal.textContent = formatter.format(quote.total ?? 0);
      renderSummaryList(summaryList, details, quote.breakdown ?? []);
      setSummaryStatus(summaryStatus, quote.message ?? 'Indicatie inclusief btw.');
    } catch (error) {
      if (requestId !== lastQuoteRequest) return;
      summaryTotal.textContent = 'n.v.t.';
      setSummaryStatus(summaryStatus, 'Kan geen verbinding maken met de prijsservice.', 'error');
    }
  };

  stepNavigation.addEventListener('click', (event) => {
    const button = event.target.closest('button');
    if (!button) return;
    event.preventDefault();
    updateStateFromInputs();
    if (button.dataset.prev !== undefined) {
      currentIndex = Math.max(0, currentIndex - 1);
    }
    if (button.dataset.next !== undefined) {
      if (currentIndex < config.steps.length - 1) {
        currentIndex += 1;
      } else {
        alert('Configuratie opgeslagen! We sturen direct een offerte per e-mail.');
      }
    }
    render();
    updateSummary();
  });

  document.querySelector('[data-action="offer"]')?.addEventListener('click', async () => {
    updateStateFromInputs();
    try {
      const quote = await requestQuote();
      alert(`Offerte aangemaakt voor ${state.naam ?? 'onbekend'}:\nTotaal: ${formatter.format(quote.total ?? 0)}`);
    } catch (error) {
      alert('Offerte genereren mislukt. Controleer of de Python-server draait.');
    }
  });

  document.querySelector('[data-action="sign"]')?.addEventListener('click', () => {
    alert('E-signature placeholder: bevestig digitaal akkoord.');
  });

  document.querySelector('[data-action="pay"]')?.addEventListener('click', () => {
    alert('Betaalmodule placeholder: iDEAL/Stripe flow opent in productie.');
  });

  document.querySelector('[data-action="schedule"]')?.addEventListener('click', () => {
    alert('Planning placeholder: beschikbare slots worden hier getoond.');
  });

  hydrateTimeline(timeline, config.timeline);
  hydrateFaq(faq, config.faq);
  attachAssistant(assistant, config);
  render();
  updateSummary();
}
