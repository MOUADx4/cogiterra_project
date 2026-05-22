# 🐘 Dashboard PHP — Cogiterra Bounces

Réécriture **100% PHP** du dashboard Streamlit, avec le même design 2026 et les **mêmes 7 onglets**.

> ✅ Lit la **même base SQLite** (`data/bounces.db`) que le pipeline Python — aucune duplication de données.

---

## 🚀 Lancement

```bash
# Depuis la racine du projet
php -S localhost:8080 -t dashboard-php/

# → http://localhost:8080
```

Aucune dépendance, aucun composer install. **PHP 8.0+** suffit.

### Vérifier la présence de PDO SQLite
```bash
php -m | grep -i pdo_sqlite
```
(devrait afficher `pdo_sqlite` — inclus par défaut dans macOS et la plupart des distros Linux)

---

## 🏗️ Architecture

```
dashboard-php/
├── index.php                 ← entry + router (?tab=...)
├── config.php                ← paths, constantes, .env loader
│
├── lib/
│   ├── db.php                ← PDO SQLite + toutes les queries
│   ├── helpers.php           ← health score, formatters dates, h(), csv
│   └── actions.php           ← adopt/reject suggestions, run pipeline, demo
│
├── api/                      ← endpoints JSON pour AJAX
│   ├── today.php             ← table filtrable
│   ├── live.php              ← feed temps réel
│   ├── adopt.php · reject.php
│   ├── poll.php · report.php ← lance main.py en sous-process
│   ├── demo.php              ← injection données démo
│   └── export_csv.php        ← export CSV (today / soft / rules)
│
├── views/                    ← 1 fichier par onglet
│   ├── _layout_top.php       ← sidebar + head
│   ├── _layout_bottom.php
│   ├── overview.php          ← KPIs · donut · Health Score · top domaines
│   ├── today.php             ← table + filtres + export
│   ├── surveillance.php      ← soft cross-jours · zones OK/Alerte/Critique
│   ├── history.php           ← stacked area 30j + perf classifier
│   ├── live.php              ← feed (refresh JS 5s)
│   ├── rules.php             ← adopter/rejeter les regex LLM
│   └── data.php              ← exploration SQLite brute
│
└── assets/
    ├── style.css             ← design 2026 (~430 lignes)
    ├── app.js                ← Plotly + AJAX + gauge SVG
    ├── cogiterra_logo.png
    └── cogiterra_logo.svg
```

---

## 🎨 Stack

| Couche | Outil |
|---|---|
| **Serveur** | PHP 8 (built-in server ou Apache/nginx) |
| **DB** | PDO SQLite (lit `data/bounces.db`) |
| **Frontend** | HTML + CSS (~430 lignes) + Plotly.js |
| **Polices** | Inter + JetBrains Mono + Material Symbols (CDN Google Fonts) |
| **Charts** | Plotly.js (CDN jsDelivr) |
| **Interactions** | Vanilla JS (fetch + AJAX, pas de framework) |

**Aucune dépendance composer.** Zéro `vendor/`. Déployable tel quel sur n'importe quel hébergement PHP.

---

## 🆚 Équivalence Streamlit ↔ PHP

| Streamlit (Python) | PHP (ce dashboard) |
|---|---|
| `st.dataframe()` | `<table class="data">` |
| `st.tabs()` | Onglets via `?tab=` + sidebar nav |
| `st.button()` + `subprocess` | `<button>` + `fetch('api/poll.php')` |
| `@st.cache_data` | PDO + cache HTTP statique |
| `plotly.express` (Python) | Plotly.js (CDN, même rendu) |
| `pd.DataFrame` | `array` PHP + `foreach` |
| `st.markdown(html, unsafe_allow_html=True)` | HTML natif |

---

## 🧪 Test rapide

```bash
# 1. Lancer le serveur
php -S localhost:8080 -t dashboard-php/

# 2. Dans un autre terminal : injecter des données démo
curl -X POST http://localhost:8080/api/demo.php

# 3. Ouvrir le dashboard
open http://localhost:8080
```

Tu devrais voir :
- 60 bounces dans **Aujourd'hui**
- 25 adresses sous surveillance dans **Surveillance**
- 30 jours d'historique avec stacked area dans **Historique**
- 5 suggestions de règles dans **Règles**

---

## ⚙️ Configuration

Aucune config nécessaire — tout est auto-chargé depuis le `.env` à la racine.
Les seuls éléments lus :
- `SOFT_BOUNCE_THRESHOLD` (défaut 5)
- `SOFT_BOUNCE_WARNING` (défaut 3)

---

## 🔗 Intégration avec le pipeline Python

Le pipeline Python (`main.py`) tourne en arrière-plan via cron :
```cron
*/5 * * * * cd /opt/cogiterra && venv/bin/python main.py --mode poll
0 6 * * *   cd /opt/cogiterra && venv/bin/python main.py --mode report
```

Le dashboard PHP **lit la même base SQLite** que ces jobs. Aucune duplication, aucune file d'attente, aucun serveur intermédiaire.

Les boutons **Poll IMAP** / **Générer rapport** du dashboard exécutent `venv/bin/python main.py --mode poll/report` en sous-processus via `proc_open()`.

---

<sub>Cogiterra Bounces · H3 NIGHT INNOVATHON 2026</sub>
