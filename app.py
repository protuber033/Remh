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

    @property
    def hero_image(self) -> str:
        return f"images/{self.id}.svg"


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

    def build_for(self, service: Service) -> None:
        color = self._color_for(service.id)
        svg = self._svg_template(service.name, service.tagline, color)
        (self.output_dir / f"{service.id}.svg").write_text(svg, encoding="utf-8")

    def _color_for(self, service_id: str) -> str:
        palette = {
            "uitbouw": "#f97316",
            "dakkapel": "#3b82f6",
            "stuc-schilder": "#8b5cf6",
            "kozijnen": "#0ea5e9",
            "loodgieter": "#14b8a6",
            "installaties": "#22c55e",
        }
        return palette.get(service_id, "#94a3b8")

    def _svg_template(self, title: str, subtitle: str, color: str) -> str:
        return f"""
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 640 360'>
  <defs>
    <linearGradient id='grad' x1='0%' y1='0%' x2='100%' y2='100%'>
      <stop offset='0%' stop-color='{color}' stop-opacity='0.95'/>
      <stop offset='100%' stop-color='{color}' stop-opacity='0.65'/>
    </linearGradient>
  </defs>
  <rect width='640' height='360' rx='28' fill='url(#grad)'/>
  <g transform='translate(60,90)'>
    <text font-family='Inter,Arial,sans-serif' font-size='44' fill='white' font-weight='700'>{title}</text>
    <text y='70' font-family='Inter,Arial,sans-serif' font-size='22' fill='white' opacity='0.9'>{subtitle}</text>
    <rect y='120' width='480' height='140' rx='18' fill='rgba(255,255,255,0.15)' stroke='rgba(255,255,255,0.4)'/>
    <line x1='60' y1='150' x2='420' y2='150' stroke='white' stroke-width='3' stroke-linecap='round' opacity='0.55'/>
    <line x1='60' y1='190' x2='420' y2='190' stroke='white' stroke-width='3' stroke-linecap='round' opacity='0.35'/>
    <circle cx='40' cy='150' r='9' fill='white'/>
    <circle cx='40' cy='190' r='9' fill='white' opacity='0.7'/>
  </g>
</svg>
"""


class SiteBuilder:
    def __init__(self, repository: ServiceRepository) -> None:
        self.repository = repository
        self.image_factory = ImageFactory(IMAGE_DIR)

    def build(self) -> None:
        PUBLIC_DIR.mkdir(exist_ok=True)
        (PUBLIC_DIR / "assets").mkdir(exist_ok=True)
        (PUBLIC_DIR / "images").mkdir(exist_ok=True)
        self._write_assets()
        self._write_index()
        for service in self.repository.all():
            self.image_factory.build_for(service)
            self._write_service_page(service)
        print("Site opgebouwd in", PUBLIC_DIR)

    def _write_assets(self) -> None:
        (ASSET_DIR / "style.css").write_text(BASE_CSS, encoding="utf-8")
        (ASSET_DIR / "app.js").write_text(BASE_JS, encoding="utf-8")

    def _write_index(self) -> None:
        cards = []
        for service in self.repository.all():
            cards.append(
                f"""
                <article class='service-card'>
                  <img src='{service.hero_image}' alt='{service.name} illustratie' loading='lazy'>
                  <div>
                    <h3>{service.name}</h3>
                    <p>{service.summary}</p>
                    <a class='btn' href='{service.id}.html'>Start</a>
                  </div>
                </article>
                """
            )
        content = INDEX_TEMPLATE.format(service_cards='\n'.join(cards))
        (PUBLIC_DIR / "index.html").write_text(content, encoding="utf-8")

    def _write_service_page(self, service: Service) -> None:
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
                      <h3>{step.label}</h3>
                      <div class='options'>{options_html}</div>
                    </section>
                    """
                )
            elif step.type == "number":
                questions.append(
                    f"""
                    <section class='question'>
                      <h3>{step.label}</h3>
                      <input type='number' name='{step.id}' min='{step.min or 0}' max='{step.max or ''}' step='1' required data-input-type='number'>
                      <p class='hint'>€{step.price_per_unit:.0f} per eenheid</p>
                    </section>
                    """
                )
        page = SERVICE_TEMPLATE.format(
            name=service.name,
            tagline=service.tagline,
            summary=service.summary,
            hero=service.hero_image,
            service_id=service.id,
            questions='\n'.join(questions),
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
:root {
  color-scheme: light dark;
  --bg: #f8fafc;
  --card: #ffffff;
  --primary: #0f172a;
  --accent: #2563eb;
  --muted: #475569;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--primary);
}
header {
  padding: 3rem 1.5rem 2rem;
  background: radial-gradient(circle at top left, #e0f2fe, #e2e8f0 55%);
  text-align: center;
}
main { padding: 2rem 1.5rem 4rem; max-width: 1080px; margin: 0 auto; }
.hero img { width: 100%; border-radius: 1.5rem; box-shadow: 0 20px 60px rgba(15,23,42,0.15); }
.service-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}
.service-card {
  background: var(--card);
  padding: 1rem;
  border-radius: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  box-shadow: 0 12px 30px rgba(15,23,42,0.12);
}
.service-card img { width: 100%; border-radius: 1rem; }
.btn {
  background: var(--accent);
  color: white;
  padding: 0.75rem 1.5rem;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  display: inline-flex;
  justify-content: center;
}
.config-layout { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 2rem; }
.config-card {
  background: var(--card);
  padding: 2rem;
  border-radius: 1.5rem;
  box-shadow: 0 20px 60px rgba(15,23,42,0.12);
}
.options { display: flex; flex-direction: column; gap: 0.75rem; }
.option { border: 1px solid #e2e8f0; border-radius: 0.85rem; padding: 0.65rem 0.9rem; display: flex; gap: 0.5rem; align-items: center; }
.option input { accent-color: var(--accent); }
.question { margin-bottom: 1.5rem; }
.hint { color: var(--muted); font-size: 0.9rem; }
.summary { background: #0f172a; color: white; border-radius: 1.5rem; padding: 2rem; display: flex; flex-direction: column; gap: 1rem; }
.summary h3 { margin: 0; }
.breakdown { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.65rem; }
.breakdown li { display: flex; justify-content: space-between; border-bottom: 1px dashed rgba(255,255,255,0.3); padding-bottom: 0.4rem; }
small { color: var(--muted); }
form button {
  width: 100%;
  margin-top: 1.5rem;
  padding: 0.85rem;
  border-radius: 999px;
  border: none;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(120deg, #2563eb, #1d4ed8);
}
.alert { padding: 0.75rem 1rem; border-radius: 0.75rem; background: #e0f2fe; color: #0c4a6e; }
"""

BASE_JS = """
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
      <h1>Bouwen & verbouwen</h1>
      <p>Configuring, offreren en plannen voor zes specialisaties vanuit één beheeromgeving.</p>
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
      <h1>{name}</h1>
      <p>{tagline}</p>
    </header>
    <main>
      <section class='config-layout'>
        <article class='config-card'>
          <img src='{hero}' alt='{name} illustratie' style='width:100%;border-radius:1rem;margin-bottom:1rem;'>
          <p>{summary}</p>
          <form data-config-form data-service-id='{service_id}'>
            <label class='question'>
              <h3>Postcode</h3>
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
