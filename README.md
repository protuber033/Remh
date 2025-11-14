# Bouwen & Verbouwen demo

Complete herbouw van de hoofdsite met zes subsites, gebouwd vanuit één Python-applicatie. Het script `app.py` genereert de volledige front-end (HTML, CSS, AI-achtige SVG's) en levert meteen een API voor prijsindicaties.

## Projectstructuur

```
.
├── app.py              # sitebuilder + API-server
├── data/services.json  # brondata voor alle diensten
├── public/             # gegenereerde site (build output)
└── README.md
```

## Benodigdheden

* Python 3.11+
* Geen extra packages nodig (alles gebruikt standaardbibliotheek)

## Site genereren

```
python app.py build
```

Dit schrijft de volledige site weg naar `public/`, inclusief nieuwe SVG-beelden per dienst, frisse CSS en de servicepagina's.

## Lokale server

```
python app.py serve --port 4173
```

* Bezoek `http://localhost:4173` voor de hoofdsite.
* De endpoint `POST /api/quote` berekent prijzen voor elke configurator.
* Zodra je een veld wijzigt, wordt er live een prijsberekening getoond.

## Deploy

* Plaats de inhoud van `public/` op elke statische hosting naar keuze.
* Draai `python app.py serve` op een backend voor het aanroepen van `/api/quote` of gebruik een serverless functie met dezelfde `PricingEngine`-logica.

## Uitbreiden

1. Voeg een dienst toe in `data/services.json`.
2. Run `python app.py build`.
3. Een nieuwe pagina + illustratie verschijnt automatisch.

Met `app.py` is de gehele hoofdsite reproduceerbaar, eenvoudig te onderhouden en consistent qua look & feel.
