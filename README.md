# 🚀 b2b-digest-agent

Micro-servizio Python interamente automatizzato che monitora fonti istituzionali (bandi pubblici, gare d'appalto e aggiornamenti normativi), sintetizza le opportunità tramite **Google Gemini Pro** con output strutturato Pydantic, e invia un digest quotidiano via **Telegram** (in formato HTML nativo) e/o **Email**.

L'esecuzione è schedulata ogni mattina tramite **GitHub Actions**, con deduplicazione automatica tramite commit su `seen_ids.json`.

---

## 📁 Struttura del Progetto

```
b2b-digest-agent/
├── .github/
│   └── workflows/
│       └── daily-digest.yml      # Automazione GitHub Actions con cron & commit push
├── src/
│   └── b2b_digest/
│       ├── __init__.py
│       ├── config.py             # Configurazione da ambiente / .env
│       ├── models.py             # Modelli Pydantic (DailyDigest, DigestItem, ecc.)
│       ├── storage.py            # Deduplicazione tramite seen_ids.json
│       ├── scraper/
│       │   ├── base.py           # BaseScraper con User-Agent browser standard
│       │   └── sources.py        # Collector RSS / fonti pubbliche
│       ├── analyzer/
│       │   └── gemini.py         # Client Gemini Pro con structured output Pydantic
│       ├── notifications/
│       │   ├── formatter.py      # Formattatori HTML (Telegram), Markdown e Email
│       │   ├── telegram.py       # Dispatcher Telegram con parse_mode="HTML"
│       │   └── email.py          # Dispatcher Email SMTP multipart
│       └── main.py               # Orchestratore e CLI
├── tests/
│   └── test_digest.py            # Suite di test unitari
├── .env.example                  # Template variabili d'ambiente
├── .gitignore                    # Esclusioni (preserva visto seen_ids.json)
├── ARCHITECTURE.md               # Architettura e diagramma di flusso Mermaid
├── pyproject.toml                # Specifiche pacchetto & dipendenze
├── requirements.txt              # Dipendenze pip
├── seen_ids.json                 # Registro ID inviati (auto-aggiornato da CI/CD)
└── README.md
```

---

## ⚙️ Installazione Locale

1. **Clona il repository**:
   ```bash
   git clone <tuo-repo-url>
   cd b2b-digest-agent
   ```

2. **Crea ed attiva un ambiente virtuale**:
   ```bash
   python -m venv .venv
   # Su Windows:
   .venv\Scripts\activate
   # Su Linux / macOS:
   source .venv/bin/activate
   ```

3. **Installa le dipendenze**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura le variabili d'ambiente**:
   Copia `.env.example` in `.env` e inserisci le tue credenziali:
   ```bash
   cp .env.example .env
   ```

---

## 🧪 Esecuzione e Test

### 1. Test in modalità simulata (--dry-run e --sample)
Esegui la pipeline senza chiamare l'API Gemini esterna (nessun costo) e senza inviare notifiche reali:
```bash
python -m b2b_digest.main --dry-run --sample
```

### 2. Esecuzione dei Test Unitari
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 🤖 Configurazione GitHub Actions

Il workflow `.github/workflows/daily-digest.yml` viene eseguito dal lunedì al venerdì alle 07:00 UTC (o manualmente da GitHub via *Run workflow*).

Configura i seguenti **Repository Secrets** in *Settings -> Secrets and variables -> Actions*:

| Nome Secret | Descrizione |
|---|---|
| `GEMINI_API_KEY` | Chiave API ottenuta da [Google AI Studio](https://aistudio.google.com/) |
| `TELEGRAM_BOT_TOKEN` | Token ottenuto da [@BotFather](https://t.me/botfather) |
| `TELEGRAM_CHAT_ID` | ID della chat o del canale Telegram di destinazione |
| `SMTP_HOST` | Host server SMTP (es. `smtp.sendgrid.net`, `smtp.gmail.com`) *(Opzionale)* |
| `SMTP_PORT` | Porta SMTP (es. `587` o `465`) *(Opzionale)* |
| `SMTP_USER` | Username / email mittente SMTP *(Opzionale)* |
| `SMTP_PASSWORD` | Password o App Password SMTP *(Opzionale)* |
| `SMTP_TO_EMAIL` | Indirizzo email destinatario *(Opzionale)* |

> [!NOTE]
> Il job GitHub Actions ha configurato `permissions: contents: write` e al termine dell'invio esegue automaticamente il commit e push del file `seen_ids.json` aggiornato.

---

## 🌐 Pubblicazione Landing Page (Waitlist in 2 Minuti a Costo Zero)

La cartella [`landing/`](landing/) contiene una landing page statica completa (HTML, CSS e JS vanilla, senza framework pesanti né dipendenze di build) pronta per validare la domanda e raccogliere lead.

### 1. Anteprima Locale
Per visualizzare subito la pagina sul tuo browser:
```bash
python -m http.server 8000 -d landing
```
Apri poi `http://localhost:8000`.

### 2. Deploy Gratuito su GitHub Pages (Opzione A)
1. Esegui il push del repository su GitHub.
2. Invia la sola cartella `landing/` sul branch `gh-pages` con un comando rapido:
   ```bash
   git subtree push --prefix landing origin gh-pages
   ```
3. Vai su **Settings -> Pages** del tuo repository e assicurati che la sorgente sia impostata su `Deploy from a branch` -> `gh-pages` / `/ (root)`. Il tuo sito sarà online in 60 secondi su `https://<tuo-username>.github.io/<tuo-repo>/`.

### 3. Deploy Gratuito su Cloudflare Pages (Opzione B - Consigliato per domini personalizzati)
1. Accedi alla dashboard di [Cloudflare Dashboard](https://dash.cloudflare.com/) -> **Workers & Pages** -> **Create application** -> **Pages**.
2. Collega il tuo repository GitHub.
3. Nella schermata di configurazione build:
   - **Framework preset:** `None`
   - **Build command:** *(lascia vuoto)*
   - **Build output directory:** `landing`
4. Clicca **Save and Deploy**. Cloudflare fornirà hosting globale ultraveloce su edge network e certificato SSL gratuito.

### 4. Collegare il Form di Iscrizione (Formspree o Webhook)
Apri [`landing/index.html`](landing/index.html) alla riga del `<form>` e incolla il tuo endpoint:
```html
<form class="waitlist-form" id="hero-waitlist-form" action="https://formspree.io/f/TUO_ID" method="POST">
```
In alternativa, puoi collegare un webhook di Make, Zapier o Google Sheets.
