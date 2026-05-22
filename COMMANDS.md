# 🚀 Commandes — Cogiterra Bounces

Toutes les commandes pour lancer le projet, le dashboard et les slides.

---

## 📦 1. Installation (une seule fois)

```bash
# Cloner le repo
git clone <repo-url> cogiterra_hackathon
cd cogiterra_hackathon

# Créer le venv et installer les dépendances
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurer les variables d'env
cp .env.example .env
# Puis éditer .env (BAL IMAP, SMTP, LLM_API_KEY, etc.)
```

> 💡 **macOS Python 3.13** — si `CERTIFICATE_VERIFY_FAILED` :
> `/Applications/Python\ 3.13/Install\ Certificates.command`

---

## ⚙️ 2. Lancer le pipeline (`main.py`)

Active toujours le venv avant : `source venv/bin/activate`

### Mode `pipe` — temps réel (Postfix, stdin)
Traite **un seul email** lu sur stdin (utilisé par Postfix en production).

```bash
python main.py --mode pipe < tests/fixtures/hard_bounce.eml
```

### Mode `poll` — IMAP périodique (cron)
Va chercher tous les nouveaux messages **UNSEEN** de la BAL bounces, les traite, puis les déplace dans le dossier `Processed`.

```bash
python main.py --mode poll
```

### Mode `report` — rapport quotidien
Agrège les bounces de la journée, génère **3 CSV** (`to_delete`, `to_pause`, `to_modify`) et les envoie par mail (+ webhook CMS si configuré, + alerte Slack si anomalie).

```bash
python main.py --mode report
```

### Logs
Tous les modes écrivent dans `logs/` (rotation auto 10 Mo × 5).

```bash
tail -f logs/app.log
```

---

## 📊 3. Lancer le dashboard

### Option A — Dashboard PHP (recommandé pour Cogiterra)
Stack 100% PHP, lit la même base SQLite que le pipeline Python.

```bash
php -S localhost:8080 -t dashboard-php/
```

➡️ **http://localhost:8080**

> Aucun `composer install` requis. Voir [`dashboard-php/README.md`](dashboard-php/README.md) pour le détail.

### Option B — Dashboard Streamlit (Python, original)

```bash
source venv/bin/activate
streamlit run dashboard/app.py
```

➡️ Ouvre automatiquement **http://localhost:8501**

### Options utiles
```bash
# Port custom
streamlit run dashboard/app.py --server.port 8080

# Accessible sur le réseau local
streamlit run dashboard/app.py --server.address 0.0.0.0

# Mode headless (pas d'ouverture auto du navigateur)
streamlit run dashboard/app.py --server.headless true
```

### Onglets disponibles
- 🎯 **Vue d'ensemble** — distribution, top domaines, Health Score
- 📅 **Aujourd'hui** — filtres + export CSV
- 👁️ **Surveillance** — soft bounces cross-jours
- 📈 **Historique 30j** — stacked area + perf classifier
- ⚡ **Activité live** — feed temps réel
- 🤖 **Règles suggérées** — adopter/rejeter les regex du LLM
- 🗂️ **Données** — exploration SQLite + export

---

## 🎬 4. Lancer les slides de présentation

Les slides sont une page HTML statique dans `docs/slides/index.html`.

### Option A — Ouvrir directement dans le navigateur
```bash
# macOS
open docs/slides/index.html

# Linux
xdg-open docs/slides/index.html

# Windows
start docs/slides/index.html
```

### Option B — Servir via un serveur HTTP local (recommandé)
Évite les problèmes de CORS si les slides chargent des assets externes.

```bash
# Python 3 (déjà installé)
cd docs/slides && python3 -m http.server 8000
```

➡️ Ouvrir **http://localhost:8000** dans le navigateur.

### Option C — Avec npx (si Node.js installé)
```bash
npx serve docs/slides
```

### Raccourcis clavier dans les slides
- **→ / Espace** : slide suivante
- **←** : slide précédente
- **F** : plein écran
- **Esc** : sortir du plein écran

---

## 🧪 5. Lancer les tests

```bash
source venv/bin/activate
python -m pytest tests/ -v
```

```bash
# Un seul module
python -m pytest tests/test_rules_engine.py -v

# Avec couverture
python -m pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

---

## 🛠️ 6. Outils & debug

```bash
# Inspecter la base SQLite
python tools/dump_db.py

# Vider la base (attention, destructif)
rm data/*.db

# Vérifier la config chargée
python -c "import config; print(vars(config))"
```

---

## ⏰ 7. Déploiement cron (production)

```cron
# Poll IMAP toutes les 5 minutes
*/5 * * * * cd /opt/cogiterra_hackathon && venv/bin/python main.py --mode poll >> logs/cron.log 2>&1

# Rapport quotidien à 6h00
0 6 * * * cd /opt/cogiterra_hackathon && venv/bin/python main.py --mode report >> logs/cron.log 2>&1
```

Pour le mode `pipe` (temps réel via Postfix) → voir [`postfix/master.cf.example`](postfix/master.cf.example).

---

## 🐳 8. Tout-en-un (recap rapide)

```bash
# Setup
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && cp .env.example .env

# Pipeline (au choix)
python main.py --mode pipe < email.eml      # temps réel
python main.py --mode poll                  # IMAP périodique
python main.py --mode report                # rapport quotidien

# Dashboard PHP (recommandé)
php -S localhost:8080 -t dashboard-php/     # http://localhost:8080

# Dashboard Streamlit (original Python)
streamlit run dashboard/app.py              # http://localhost:8501

# Slides
open docs/slides/index.html                 # direct
# ou
cd docs/slides && python3 -m http.server 8000   # http://localhost:8000

# Tests
python -m pytest tests/ -v
```

---

<div align="center">
<sub>Cogiterra Bounces — H3 NIGHT INNOVATHON 2026</sub>
</div>
