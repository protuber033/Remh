# Digitale klantreis platform voor bouw- en installatiediensten

## 1. Overzicht
Deze proposal beschrijft hoe we een hoofdsite met zes subsites opleveren waarin bezoekers een volledige online klantreis doorlopen: configurator → prijs/offerte → akkoord + e-signature → iDEAL-aanbetaling → planning. Het platform is schaalbaar, mobiel-first en eenvoudig te beheren door het interne team.

## 2. Architectuurkeuze
| Component | Keuze | Toelichting |
| --- | --- | --- |
| Front-end | Next.js 14 (App Router) + Tailwind CSS + shared component library | SSR/ISR voor snelle laadtijden, gedeeld design system voor hoofd- en subsites, theming per dienst via CMS-config. |
| CMS | Strapi Cloud (EU) | Eén beheeromgeving voor content, prijsregels, FAQ/AI-kennisbank, e-mailtemplates. Rollen/ rechten voor marketing, sales, planning. |
| Pricing & configurators | Custom Next.js server actions + Strapi price tables | Alle logica in gedeelde service met multipliers (regio/workload/korting). Configurators per subsite halen schema + labels + validatie uit CMS zodat marketing opties kan beheren. |
| Offerte/PDF | microservice (Node) met @react-pdf/renderer + CDN voor AI-beelden | Genereert PDF + e-mailbijlagen, slaat versies op in object storage (S3). |
| Betaling | Stripe Payment Element (iDEAL + cards) | Eén integratie voor aanbetalingen + betaalde opnames. Webhooks sturen status naar CRM + Strapi. |
| Planning | Cal.com (self-hosted) gekoppeld aan Stripe sessie | Directe slotkeuze na betaling. Custom embed + webhooks naar CRM. |
| CRM | HubSpot (Operations Starter) | Leads, offertes, betalingen en planning updates per dienstpipeline. |
| AI-assistent | Azure OpenAI GPT-4o mini + Retrieval Augmented Generation (Strapi content) | Geïntegreerde chat-widget met guardrails, logging van vragen + antwoorden in CRM. |
| Hosting | Vercel (front-end) + Strapi Cloud (CMS) + Railway (PDF service) | EU-datacenters, automatische SSL, staging-omgeving, CI/CD. |

## 3. Informatiearchitectuur
```
bedrijf.nl (hoofdnavigatie + merk)
├── /uitbouw
├── /dakkapel
├── /stuc-schilder
├── /kunststof-kozijnen-schuifpuien-deuren
├── /loodgieter
└── /installatie-ketel-warmtepomp-airco-zonnepanelen
```
Alle subsites delen hero-componenten, configurator-shell, testimonials, FAQ en CTA's. SEO-structuur: schema.org `Service` + `Product`, XML-sitemaps, canonical tags.

## 4. Configurators
* 5–10 stappen, swipeable cards mobiel, sticky prijs & samenvatting.
* Schema in CMS definieert velden, validatie, prijsregels en "bijzondere aanvraag"-flags.
* Real-time prijscomponent berekent:
  `totaal = (basis + opties) × region_multiplier × workload_factor × rush_factor – korting`
* Opslaan van partiële leads (voor remarketing) met consent.

### Voorbeeld Sub 1 – Uitbouw
1. **Locatie**: postcode + huisnr → region multiplier.
2. **Afmeting**: breedte/diepte (validatie ≤4 m); berekent m² × €2.100.
3. **Dak & daglicht**: plat/schuin + lichtopties (prijzen volgens briefing).
4. **Gevel/pui**: type schuif/vouwwand, glasopties, roosters.
5. **Fundering & vloer**: stroken standaard, andere route naar betaalde opname.
6. **Binnenafwerking & elektra**: stuc, schilder, stopcontacten/lichtpunten.
7. **Vergunning & bijzondere situatie**: bij monumenten → doorverwijzen.
8. **Planning & spoed**: spoed activeert rush factor +10%.
9. **Gegevens**: gegevens, uploads, akkoord voorwaarden.

Alle andere subsites volgen vergelijkbare detailstappen zoals in de opdracht beschreven (dakkapel, stuc/schilder, kozijnen, loodgieter, installatie).

## 5. Offerteflow
1. Configuratie → JSON payload opgeslagen in Strapi + HubSpot deal.
2. AI-illustratie service genereert 2–4 beelden volgens prompts (per type).
3. PDF-service bouwt offerte met:
   * prijsregels (excl/incl btw)
   * specificaties per stap + disclaimers (vergunning, illustraties)
   * AI-visuals en iconen
   * CTA-knoppen: "Akkoord" en "Plan uitvoer".
4. PDF en e-mail worden automatisch verzonden (Resend API). Downloadknop beschikbaar.

## 6. Akkoord, e-signature & betaling
* Klik-akkoord + DocuSign eSignature embedded voor juridische handtekening.
* Na handtekening wordt Stripe Payment Element geladen (iDEAL default). Minimale aanbetaling configureerbaar per dienst.
* Webhook flow:
  1. `signature.completed` → update HubSpot deal.
  2. `checkout.session.completed` → markeer betaald, stuur factuur + boekingslink.
  3. Cal.com booking → bevestigingsmail + ICS + CRM update.

## 7. AI-assistent
* Widget in footer + sticky help-knop.
* Ingest: Strapi FAQ, voorwaarden, prijsdisclaimers. Vector DB (Pinecone EU) met daily sync.
* Guardrails: detection van buiten-scope → automatische call-to-action "Plan betaalde opname".
* Logging: elk gesprek gekoppeld aan lead ID; exporteerbaar.

## 8. Toegankelijkheid & performance
* WCAG 2.1 AA checklist in CI (Pa11y) + axe-linters.
* Core Web Vitals budget: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1.
* Optimalisaties: image CDN (Vercel), priority hints, route prefetching, lazy-loaded configurator steps.
* Cookie banner (Consent Mode v2) + server-side GTM events (configurator start, offerte, akkoord, betaling, planning).

## 9. Beheer & workflows
* Strapi Collections: Pages, Configurators, PriceOptions, FAQs, AI-Knowledge, EmailTemplates.
* Workflows: Marketing update content → Publish; Sales monitort HubSpot pipelines; Planning beheert Cal.com resources & blackout dates.
* Dashboard (Next.js) met overzicht van leads/offertes/orders + exports.

## 10. Implementatieplan (12 weken)
1. **Week 1-2** – Discovery & UX: wireframes, content map, data- en prijsmodel, CRM setup.
2. **Week 3-5** – CMS & front-end foundation: Strapi schemas, Next.js shell, theming, accessibility tokens.
3. **Week 6-7** – Configurators + pricing engine + AI-illustratie pipeline.
4. **Week 8** – Offerte/PDF + e-signature integratie.
5. **Week 9** – Payments (Stripe iDEAL) + Cal.com booking + webhook orchestration.
6. **Week 10** – AI-assistent & knowledge base.
7. **Week 11** – QA: WCAG audits, Lighthouse, load tests, security hardening.
8. **Week 12** – Content migration, training, go-live + monitoring.

## 11. Acceptatie & training
* Testcases per subsite (configurator → offerte → betaling → planning) gedocumenteerd in Notion.
* Training sessie voor marketing (CMS), sales (HubSpot), planning (Cal.com), support (AI logging).
* Beheergids bevat instructies voor prijsupdates, FAQ-wijzigingen, e-mail templates.

## 12. Volgende stappen
* Finaliseer huisstijl & content.
* Lever product- en prijsdata aan voor Strapi import.
* Bespreek hosting/contracten (Vercel, Stripe, DocuSign, Cal.com, HubSpot, Azure OpenAI).
* Start sprint 1 na akkoord.
