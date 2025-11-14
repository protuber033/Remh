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

## Resultaat lokaal bekijken (stapsgewijs)

1. **Dependencies controleren** – Python 3.10+ is voldoende; er zijn geen externe packages nodig.
2. **Server starten** – Voer vanuit de projectroot het volgende uit:

   ```bash
   python server.py --port 4173
   ```

3. **Browser openen** – Navigeer naar <http://localhost:4173>. Je ziet nu de hoofdsite en kunt doorlinken naar alle subsites.
4. **API checken (optioneel)** – Elke configurator verstuurt een `POST /api/quote`-request met een payload zoals `{"service": "uitbouw", "payload": {...}}`. De server handelt deze af en stuurt de prijs terug.
5. **Aanpassingen testen** – Omdat alle subsites dezelfde `assets/styles.css` en `assets/main.js` delen, zie je front-end wijzigingen direct op iedere pagina.

## Wijzigingen committen & pushen naar GitHub

1. **Status controleren** – `git status` toont welke bestanden gewijzigd zijn.
2. **Bestanden selecteren** – Gebruik `git add pad/naar/bestand` (of `git add .` voor alles) om ze klaar te zetten.
3. **Commit maken** – `git commit -m "beschrijving van de wijziging"` legt je update vast in de lokale repository.
4. **Branch kiezen (indien nodig)** – Maak een feature-branch aan met `git checkout -b mijn-branch` als je niet direct op `main` wilt werken.
5. **Pushen naar GitHub** – Verstuur de commit(s) met `git push origin <branch-naam>`.
6. **Pull Request openen** – Ga naar GitHub, kies je branch en klik op “Compare & pull request” om je werk te laten reviewen.

> Tip: run na grote wijzigingen opnieuw `python server.py --port 4173` om te controleren of alles lokaal nog steeds werkt voordat je commit.

## Volgende stappen

* Koppel de offerte-/betalingsknoppen aan echte API’s (DocuSign, Stripe, Cal.com).
* Vervang de placeholders voor AI-visuals door een server-side image-service.
* Sluit een headless CMS of WordPress-multisite aan om content, prijzen en FAQ’s te beheren zonder code.
