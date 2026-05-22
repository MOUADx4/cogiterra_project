# 🎬 Enregistrer le GIF de démo pour le README

Place le GIF final dans `docs/demo.gif` (le README le référence
déjà à cet emplacement).

## Outils recommandés (Mac)

### Option A — Kap (open source, recommandé)
```bash
brew install --cask kap
```
- Limite la zone d'enregistrement à la fenêtre du dashboard
- Format : **GIF**, **15 fps**, largeur ~1200px
- Durée idéale : **15–25 secondes**

### Option B — CleanShot X (payant, plus pro)
- Très bonne qualité, taille de fichier optimisée
- Export GIF avec compression réglable

### Option C — Terminal + asciinema (pour montrer une commande)
```bash
brew install asciinema
asciinema rec demo.cast
# Joue la commande puis Ctrl+D
# Convertir en GIF avec agg ou asciinema-edit
```

## Script de démo (15 secondes)

1. **(0-3s)** Dashboard ouvert, vue d'ensemble — montre le bento grid + Health Score
2. **(3-6s)** Sidebar → clic sur **"✨ Injecter données démo"**
3. **(6-9s)** Navigation : onglet **Aujourd'hui** → un filtre rapide
4. **(9-12s)** Onglet **🤖 Règles suggérées** → clic **Adopter** sur une suggestion
5. **(12-15s)** Sidebar → clic **"📤 Générer rapport"** → toast "Rapport envoyé"

## Compression / optimisation

```bash
# Si le GIF est trop lourd (> 5 Mo)
gifsicle -O3 --lossy=80 demo.gif -o demo.gif

# Ou en MP4 (mieux pour GitHub) :
ffmpeg -i demo.mov -vf "fps=15,scale=1200:-1:flags=lanczos" -c:v libx264 -crf 23 demo.mp4
```

## Screenshots statiques (alternative au GIF)

Si tu n'as pas le temps de faire un GIF, mets 2–3 screenshots dans
`docs/screenshots/` :
- `01-overview.png` (vue d'ensemble)
- `02-rules-suggested.png` (onglet règles)
- `03-historique.png` (graphique 30j)

Le README peut les afficher en ligne avec :
```markdown
![Vue d'ensemble](docs/screenshots/01-overview.png)
```
