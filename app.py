"""Centrale sitebuilder + API-server voor hoofdsite en zes subsites.

Gebruik:
    python app.py build   # genereer HTML, assets en AI-plaatjes
    python app.py serve   # start server op http://localhost:4173
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
PUBLIC_DIR = ROOT / "public"
ASSET_DIR = PUBLIC_DIR / "assets"
IMAGE_DIR = PUBLIC_DIR / "images"


@dataclass
class Option:
    label: str
    value: str
    price: float = 0.0


@dataclass
class Step:
    id: str
    label: str
    type: str
    options: List[Option] = field(default_factory=list)
    min: Optional[float] = None
    max: Optional[float] = None
    price_per_unit: Optional[float] = None


@dataclass
class Service:
    id: str
    name: str
    tagline: str
    summary: str
    base_price: float
    cta: str
    steps: List[Step]
    highlights: List[str] = field(default_factory=list)

    @property
    def hero_image(self) -> str:
        return f"images/{self.id}-hero.svg"


@dataclass
class ImageSet:
    hero: str
    detail: str
    blueprint: str


class ServiceRepository:
    def __init__(self, data_path: Path) -> None:
        self._services = self._load(data_path)

    def _load(self, data_path: Path) -> Dict[str, Service]:
        payload = json.loads(data_path.read_text())
        services = {}
        for raw in payload["services"]:
            steps = []
            for step in raw["steps"]:
                options = [Option(**opt) for opt in step.get("options", [])]
                steps.append(
                    Step(
                        id=step["id"],
                        label=step["label"],
                        type=step["type"],
                        options=options,
                        min=step.get("min"),
                        max=step.get("max"),
                        price_per_unit=step.get("price_per_unit"),
                    )
                )
            services[raw["id"]] = Service(
                id=raw["id"],
                name=raw["name"],
                tagline=raw["tagline"],
                summary=raw["summary"],
                base_price=float(raw["base_price"]),
                cta=raw["cta"],
                steps=steps,
                highlights=raw.get("highlights", []),
            )
        return services

    def all(self) -> List[Service]:
        return list(self._services.values())

    def get(self, service_id: str) -> Service:
        if service_id not in self._services:
            raise KeyError(service_id)
        return self._services[service_id]


class PricingEngine:
    def __init__(self, repository: ServiceRepository) -> None:
        self.repository = repository

    def quote(self, service_id: str, answers: Dict[str, Any], postcode: Optional[str]) -> Dict[str, Any]:
        service = self.repository.get(service_id)
        subtotal = service.base_price
        breakdown: List[Dict[str, Any]] = [
            {"label": "Basispakket", "amount": service.base_price}
        ]
        for step in service.steps:
            value = answers.get(step.id)
            if value in (None, ""):
                continue
            if step.type == "choice":
                match = next((opt for opt in step.options if opt.value == value), None)
                if match:
                    subtotal += match.price
                    breakdown.append({"label": f"{step.label}: {match.label}", "amount": match.price})
            elif step.type == "number" and step.price_per_unit:
                units = float(value)
                units = max(step.min or units, min(step.max or units, units))
                amount = units * step.price_per_unit
                subtotal += amount
                breakdown.append({"label": f"{step.label} ({units:.0f} eenheden)", "amount": amount})
        multiplier = self._region_multiplier(postcode)
        total = subtotal * multiplier
        breakdown.append({"label": "Regiofactor", "amount": round((multiplier - 1) * subtotal, 2)})
        return {
            "service": service.name,
            "subtotal": round(subtotal, 2),
            "total": round(total, 2),
            "currency": "EUR",
            "breakdown": breakdown,
            "message": self._quote_message(total)
        }

    def _region_multiplier(self, postcode: Optional[str]) -> float:
        if not postcode:
            return 1.0
        digits = ''.join(ch for ch in postcode if ch.isdigit())
        if not digits:
            return 1.0
        number = int(digits[:2])
        return 1.05 if number < 30 else 1.0 if number < 50 else 0.97

    def _quote_message(self, total: float) -> str:
        if total < 5000:
            return "Plan direct een online afspraak voor een snelle uitvoering."
        if total < 15000:
            return "We bieden montage binnen 6 weken inclusief vergunningcheck."
        return "Je ontvangt binnen 24 uur een compleet projectplan en planning."


class ImageFactory:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_for(self, service: Service) -> ImageSet:
        color = self._color_for(service.id)
        hero_name = f"{service.id}-hero.svg"
        detail_name = f"{service.id}-detail.svg"
        blueprint_name = f"{service.id}-blueprint.svg"
        (self.output_dir / hero_name).write_text(self._hero_svg(service, color), encoding="utf-8")
        (self.output_dir / detail_name).write_text(self._detail_svg(service, color), encoding="utf-8")
        (self.output_dir / blueprint_name).write_text(self._blueprint_svg(service, color), encoding="utf-8")
        return ImageSet(
            hero=f"images/{hero_name}",
            detail=f"images/{detail_name}",
            blueprint=f"images/{blueprint_name}",
        )

    def _color_for(self, service_id: str) -> str:
        palette = {
            "uitbouw": "#fb923c",
            "dakkapel": "#60a5fa",
            "stuc-schilder": "#c084fc",
            "kozijnen": "#38bdf8",
            "loodgieter": "#2dd4bf",
            "installaties": "#86efac",
        }
        return palette.get(service_id, "#94a3b8")

    def _hero_svg(self, service: Service, color: str) -> str:
        return f"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 360'>
  <defs>
    <linearGradient id='grad' x1='0%' y1='0%' x2='100%' y2='100%'>
      <stop offset='0%' stop-color='{color}' stop-opacity='0.95'/>
      <stop offset='100%' stop-color='{color}' stop-opacity='0.55'/>
    </linearGradient>
    <linearGradient id='shine' x1='0' y1='0' x2='0' y2='1'>
      <stop offset='0' stop-color='rgba(255,255,255,0.7)'/>
      <stop offset='1' stop-color='rgba(255,255,255,0.1)'/>
    </linearGradient>
  </defs>
  <rect width='640' height='360' rx='32' fill='url(#grad)'/>
  <g transform='translate(60,80)'>
    <text font-family='Manrope,Inter,sans-serif' font-size='42' fill='white' font-weight='700'>{service.name}</text>
    <text y='60' font-family='Manrope,Inter,sans-serif' font-size='20' fill='white' opacity='0.92'>{service.tagline}</text>
    <rect y='120' width='480' height='150' rx='26' fill='rgba(15,23,42,0.18)' stroke='rgba(255,255,255,0.45)'/>
    <g transform='translate(40,150)' stroke='white' stroke-linecap='round'>
      <line x1='0' y1='0' x2='380' y2='0' stroke-width='6' opacity='0.7'/>
      <line x1='0' y1='34' x2='320' y2='34' stroke-width='5' opacity='0.5'/>
      <line x1='0' y1='68' x2='260' y2='68' stroke-width='4' opacity='0.35'/>
    </g>
    <rect x='360' y='-20' width='180' height='120' rx='20' fill='url(#shine)' opacity='0.6'/>
  </g>
</svg>
"""

    def _detail_svg(self, service: Service, color: str) -> str:
        return f"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 420 260'>
  <defs>
    <linearGradient id='detail' x1='0%' y1='0%' x2='100%' y2='0%'>
      <stop offset='0%' stop-color='{color}' stop-opacity='0.35'/>
      <stop offset='100%' stop-color='{color}' stop-opacity='0.8'/>
    </linearGradient>
  </defs>
  <rect width='420' height='260' rx='26' fill='#0f172a'/>
  <g fill='none' stroke='url(#detail)' stroke-width='3' opacity='0.7'>
    <rect x='40' y='40' width='340' height='180' rx='18'/>
    <line x1='40' y1='120' x2='380' y2='120'/>
    <line x1='140' y1='40' x2='140' y2='220'/>
  </g>
  <g fill='white' font-family='Manrope,Inter,sans-serif' font-size='16'>
    <text x='60' y='90'>Stap 1</text>
    <text x='170' y='90'>Stap 2</text>
    <text x='280' y='90'>Stap 3</text>
    <text x='60' y='190'>Stap 4</text>
    <text x='170' y='190'>Stap 5</text>
    <text x='280' y='190'>Stap 6</text>
  </g>
  <circle cx='360' cy='220' r='18' fill='url(#detail)'/>
  <text x='360' y='226' text-anchor='middle' font-family='Manrope,Inter,sans-serif' font-size='12' fill='#0f172a'>config</text>
</svg>
"""

    def _blueprint_svg(self, service: Service, color: str) -> str:
        return f"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 420 260'>
  <rect width='420' height='260' rx='24' fill='#e2e8f0'/>
  <g stroke='{color}' stroke-width='2' fill='none' opacity='0.8'>
    <rect x='40' y='30' width='340' height='200' rx='18'/>
    <rect x='70' y='60' width='120' height='80' rx='10'/>
    <rect x='220' y='60' width='140' height='80' rx='10'/>
    <rect x='70' y='160' width='120' height='50' rx='10'/>
    <rect x='220' y='160' width='140' height='50' rx='10'/>
    <line x1='210' y1='60' x2='210' y2='210' stroke-dasharray='6 6'/>
  </g>
  <text x='60' y='230' font-family='Manrope,Inter,sans-serif' font-size='18' fill='#0f172a'>{service.name}</text>
</svg>
"""


class SiteBuilder:
    def __init__(self, repository: ServiceRepository) -> None:
        self.repository = repository
        self.image_factory = ImageFactory(IMAGE_DIR)
        self.image_sets: Dict[str, ImageSet] = {}

    def build(self) -> None:
        PUBLIC_DIR.mkdir(exist_ok=True)
        (PUBLIC_DIR / "assets").mkdir(exist_ok=True)
        (PUBLIC_DIR / "images").mkdir(exist_ok=True)
        self._write_assets()
        for service in self.repository.all():
            images = self.image_factory.build_for(service)
            self.image_sets[service.id] = images
            self._write_service_page(service, images)
        self._write_index()
        print("Site opgebouwd in", PUBLIC_DIR)

    def _write_assets(self) -> None:
        (ASSET_DIR / "style.css").write_text(BASE_CSS, encoding="utf-8")
        (ASSET_DIR / "app.js").write_text(BASE_JS, encoding="utf-8")

    def _write_index(self) -> None:
        cards = []
        for service in self.repository.all():
            images = self.image_sets.get(service.id)
            hero = images.hero if images else service.hero_image
            highlights = '\n'.join(f"<span>{text}</span>" for text in service.highlights[:2])
            cards.append(
                f"""
                <article class='service-card'>
                  <img src='{hero}' alt='{service.name} illustratie' loading='lazy'>
                  <div>
                    <p class='eyebrow'>Configurator</p>
                    <h3>{service.name}</h3>
                    <p>{service.summary}</p>
                    <div class='chips'>{highlights}</div>
                    <a class='btn' href='{service.id}.html'>{service.cta}</a>
                  </div>
                </article>
                """
            )
        content = INDEX_TEMPLATE.format(service_cards='\n'.join(cards))
        (PUBLIC_DIR / "index.html").write_text(content, encoding="utf-8")

    def _write_service_page(self, service: Service, images: ImageSet) -> None:
        questions = []
        for step in service.steps:
            if step.type == "choice":
                options_html = '\n'.join(
                    f"<label class='option'>"
                    f"<input type='radio' name='{step.id}' value='{opt.value}' required>"
                    f"<span>{opt.label} <small>+€{opt.price:,.0f}</small></span>"
                    f"</label>" for opt in step.options
                )
                questions.append(
                    f"""
                    <section class='question'>
                      <div class='question-heading'>
                        <span class='eyebrow'>Stap</span>
                        <h3>{step.label}</h3>
                      </div>
                      <div class='options'>{options_html}</div>
                    </section>
                    """
                )
            elif step.type == "number":
                questions.append(
                    f"""
                    <section class='question'>
                      <div class='question-heading'>
                        <span class='eyebrow'>Stap</span>
                        <h3>{step.label}</h3>
                      </div>
                      <input type='number' name='{step.id}' min='{step.min or 0}' max='{step.max or ''}' step='1' required data-input-type='number'>
                      <p class='hint'>€{step.price_per_unit:.0f} per eenheid</p>
                    </section>
                    """
                )
        highlights = '\n'.join(f"<li><span>✦</span>{text}</li>" for text in service.highlights)
        page = SERVICE_TEMPLATE.format(
            name=service.name,
            tagline=service.tagline,
            summary=service.summary,
            hero=images.hero,
            detail=images.detail,
            blueprint=images.blueprint,
            service_id=service.id,
            questions='\n'.join(questions),
            highlights=highlights,
        )
        (PUBLIC_DIR / f"{service.id}.html").write_text(page, encoding="utf-8")


class QuoteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, engine: PricingEngine, directory: str, **kwargs):
        self.engine = engine
        super().__init__(*args, directory=directory, **kwargs)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/quote":
            return super().do_POST()
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            service_id = payload.get("service_id")
            answers = payload.get("answers", {})
            postcode = payload.get("postcode")
            quote = self.engine.quote(service_id, answers, postcode)
            self._send_json(HTTPStatus.OK, quote)
        except KeyError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Service niet gevonden: {exc}"})
        except Exception as exc:  # pylint: disable=broad-except
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap');
:root {
  --bg: #f6f6f9;
  --card: #ffffff;
  --ink: #0f172a;
  --muted: #475569;
  --accent: #2563eb;
  --accent-2: #7c3aed;
  --border: #e2e8f0;
  font-family: 'Manrope', 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at 20% 20%, rgba(96,165,250,0.2), transparent 45%), var(--bg);
  color: var(--ink);
}
img { max-width: 100%; display: block; }
a { color: inherit; }
header {
  padding: clamp(2rem, 6vw, 4rem) 1.5rem;
  text-align: center;
  background: linear-gradient(120deg, rgba(37,99,235,0.08), rgba(124,58,237,0.08));
}
header h1 {
  margin-bottom: 0.75rem;
  font-size: clamp(2.2rem, 6vw, 3.3rem);
}
header p {
  max-width: 640px;
  margin: 0 auto;
  color: var(--muted);
}
main {
  max-width: 1200px;
  margin: 0 auto;
  padding: clamp(2rem, 5vw, 4rem) 1.5rem 5rem;
}
.hero img {
  width: 100%;
  border-radius: 1.5rem;
  box-shadow: 0 30px 90px rgba(15,23,42,0.12);
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.2em;
  font-size: 0.75rem;
  color: var(--accent);
}
.service-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}
.service-card {
  background: var(--card);
  border-radius: 1.5rem;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  border: 1px solid rgba(255,255,255,0.9);
  box-shadow: 0 25px 60px rgba(15,23,42,0.08);
  transition: transform 200ms ease, box-shadow 200ms ease;
}
.service-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 35px 80px rgba(15,23,42,0.15);
}
.service-card h3 { margin: 0.4rem 0; }
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.chips span {
  background: rgba(37,99,235,0.1);
  color: var(--accent);
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.85rem;
}
.btn {
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: white;
  padding: 0.85rem 1.25rem;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  margin-top: auto;
  display: inline-flex;
  justify-content: center;
  transition: opacity 150ms ease;
}
.btn:hover { opacity: 0.9; }

.service-hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 2rem;
  align-items: center;
  margin-bottom: 3rem;
}
.service-hero .gallery {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}
.gallery-mini {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1rem;
}
.gallery img {
  border-radius: 1.5rem;
  box-shadow: 0 25px 80px rgba(15,23,42,0.12);
}
.highlights {
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.highlights li {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  font-weight: 500;
}
.highlights span {
  background: rgba(124,58,237,0.15);
  color: var(--accent-2);
  width: 32px;
  height: 32px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}
.config-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 2rem;
}
.config-card {
  background: var(--card);
  padding: 2rem;
  border-radius: 1.75rem;
  box-shadow: 0 35px 90px rgba(15,23,42,0.12);
}
form input[type="text"],
form input[type="number"] {
  width: 100%;
  padding: 0.85rem 1rem;
  border-radius: 1rem;
  border: 1px solid var(--border);
  font-size: 1rem;
}
form input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37,99,235,0.15);
}
.options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.option {
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 0.85rem 1rem;
  display: flex;
  gap: 0.5rem;
  align-items: center;
  justify-content: space-between;
}
.option span { flex: 1; display: flex; justify-content: space-between; gap: 1rem; }
.option input { accent-color: var(--accent); }
.question { margin-bottom: 1.75rem; }
.question-heading h3 { margin: 0.2rem 0; }
.hint { color: var(--muted); font-size: 0.9rem; }
.summary {
  background: #0f172a;
  color: white;
  border-radius: 1.75rem;
  padding: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 2rem;
}
.summary.is-loading { opacity: 0.7; }
.summary strong {
  font-size: 2.5rem;
  letter-spacing: -0.03em;
}
.breakdown {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.breakdown li {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px dashed rgba(255,255,255,0.25);
  padding-bottom: 0.35rem;
}
form button {
  width: 100%;
  margin-top: 1.5rem;
  padding: 0.95rem;
  border-radius: 1.25rem;
  border: none;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(130deg, var(--accent), var(--accent-2));
  box-shadow: 0 20px 50px rgba(37,99,235,0.35);
  cursor: pointer;
}
.alert {
  padding: 0.9rem 1rem;
  border-radius: 1rem;
  background: rgba(37,99,235,0.12);
  color: #0c4a6e;
  margin-bottom: 2rem;
}
@media (max-width: 640px) {
  .summary { position: static; }
}

"""


BASE_JS = """
async function requestQuote(form, serviceId) {
  const formData = new FormData(form);
  const answers = {};
  for (const [key, value] of formData.entries()) {
    if (!value || key === 'postcode') continue;
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
    throw new Error('Serverfout, probeer opnieuw.');
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
  const totalField = summary.querySelector('[data-total]');

  async function update() {
    summary.classList.add('is-loading');
    try {
      const quote = await requestQuote(form, serviceId);
      totalField.textContent = `\u20AC ${quote.total.toLocaleString('nl-NL')}`;
      breakdown.innerHTML = '';
      quote.breakdown.forEach(row => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${row.label}</span><strong>\u20AC ${Number(row.amount).toLocaleString('nl-NL')}</strong>`;
        breakdown.appendChild(li);
      });
      message.textContent = quote.message;
    } catch (err) {
      message.textContent = err.message;
    } finally {
      summary.classList.remove('is-loading');
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

"""

INDEX_TEMPLATE = """

<!doctype html>
<html lang='nl'>
  <head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>Bouwen & Verbouwen – zes diensten één platform</title>
    <link rel='stylesheet' href='assets/style.css'/>
  </head>
  <body>
    <header>
      <p class='eyebrow'>Hoofdsite</p>
      <h1>Bouwen & verbouwen</h1>
      <p>Één configurator-platform voor uitbouwen, dakkapellen, afwerking, kozijnen, loodgieterspakketten en installaties.</p>
    </header>
    <main>
      <section class='hero'>
        <p class='alert'>Elke configurator levert direct een offerte, betaallink en planvoorstel.</p>
      </section>
      <section class='service-grid'>
        {service_cards}
      </section>
    </main>
  </body>
</html>

"""


SERVICE_TEMPLATE = """
<!doctype html>
<html lang='nl'>
  <head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>{name} configurator</title>
    <link rel='stylesheet' href='assets/style.css'/>
  </head>
  <body>
    <header>
      <p class='eyebrow'>Configurator</p>
      <h1>{name}</h1>
      <p>{tagline}</p>
    </header>
    <main>
      <section class='service-hero'>
        <div>
          <p class='alert'>{summary}</p>
          <ul class='highlights'>
            {highlights}
          </ul>
        </div>
        <div class='gallery'>
          <img src='{hero}' alt='{name} hero visualisatie'>
          <div class='gallery-mini'>
            <img src='{detail}' alt='{name} stappen visual'>
            <img src='{blueprint}' alt='{name} blauwdruk'>
          </div>
        </div>
      </section>
      <section class='config-layout'>
        <article class='config-card'>
          <form data-config-form data-service-id='{service_id}'>
            <label class='question'>
              <div class='question-heading'>
                <span class='eyebrow'>Stap</span>
                <h3>Postcode</h3>
              </div>
              <input type='text' name='postcode' placeholder='1234AB' required maxlength='6'>
            </label>
            {questions}
            <button type='submit'>Bereken prijs & offerte</button>
          </form>
        </article>
        <aside class='summary' data-summary>
          <h3>Indicatieve offerte</h3>
          <strong data-total>€ 0</strong>
          <ul class='breakdown' data-breakdown></ul>
          <p data-message>Resultaat verschijnt hier.</p>
        </aside>
      </section>
    </main>
    <script src='assets/app.js' defer></script>
  </body>
</html>
"""



def build_site() -> None:
    repository = ServiceRepository(DATA_DIR / "services.json")
    SiteBuilder(repository).build()


def serve_site(port: int) -> None:
    repository = ServiceRepository(DATA_DIR / "services.json")
    engine = PricingEngine(repository)
    handler = lambda *args, **kwargs: QuoteHandler(*args, directory=str(PUBLIC_DIR), engine=engine, **kwargs)
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    print(f"Server draait op http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gestopt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Site builder en server")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Genereer HTML + assets")
    serve_cmd = sub.add_parser("serve", help="Start de lokale server")
    serve_cmd.add_argument("--port", type=int, default=4173)

    args = parser.parse_args()
    if args.command == "build":
        build_site()
    elif args.command == "serve":
        if not PUBLIC_DIR.exists():
            build_site()
        serve_site(args.port)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
