# Bouw & Verbouw platform (demo)

Deze repository bevat een statische demo van de hoofdsite met zes subsites zoals beschreven in de opdracht. Elke subsite heeft een eigen configurator met live prijsindicatie, samenvatting en placeholders voor offerte, e-signature, betaling (Stripe/iDEAL) en planning (Cal.com).

## Structuur

```
site/
├─ index.html                → hoofdsite met overzicht diensten en klantreis
├─ assets/
│  ├─ styles.css             → gedeeld design system
│  └─ main.js                → gedeelde configurator-logica
└─ services/
   ├─ uitbouw.html           → sub 1
   ├─ dakkapel.html          → sub 2
   ├─ stuc-schilder.html     → sub 3
   ├─ kozijnen.html          → sub 4
   ├─ loodgieter.html        → sub 5
   └─ installaties.html      → sub 6
```

## Lokaal testen

De configurators rekenen hun prijzen nu uit via een Python-service. Start deze server vanuit de projectroot:

```bash
python server.py --port 4173
```

Open daarna <http://localhost:4173> in je browser. De server:

* dient alle statische assets uit de map `site/`;
* exposeert `POST /api/quote` voor prijsberekeningen (`{"service": "uitbouw", "payload": {...}}`).

Alle subsites gebruiken dezelfde stylesheet en configurator-script, dus wijzigingen in `assets/` gelden voor de hele omgeving.

## Volgende stappen

* Koppel de offerte-/betalingsknoppen aan echte API’s (DocuSign, Stripe, Cal.com).
* Vervang de placeholders voor AI-visuals door een server-side image-service.
* Sluit een headless CMS of WordPress-multisite aan om content, prijzen en FAQ’s te beheren zonder code.
