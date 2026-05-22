# 📐 Schémas Mermaid — version conforme au projet

Trois schémas corrigés et adaptés à l'état réel du projet **Cogiterra Bounces**.

> 🎯 **Comment les utiliser dans `index.html`**
>
> 1. Inclure Mermaid une seule fois dans le `<head>` :
>    ```html
>    <script type="module">
>      import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
>      mermaid.initialize({ startOnLoad: true, theme: 'dark' });
>    </script>
>    ```
> 2. Coller chaque bloc dans une slide :
>    ```html
>    <div class="mermaid">
>      ...code Mermaid ci-dessous...
>    </div>
>    ```
>
> Ou bien : intégrer directement la page `schemas.html` en iframe.

---

## 🔧 Différences avec les schémas d'origine

| Élément manquant / faux dans l'original | Corrigé dans cette version |
|---|---|
| ❌ LLM Claude Haiku absent | ✅ Ajouté comme fallback (uniquement si confiance < 0.80) |
| ❌ SQLite absente | ✅ Stockage central matérialisé |
| ❌ Dashboard Streamlit absent | ✅ Connecté à SQLite |
| ❌ Webhook CMS absent | ✅ Sortie séparée |
| ❌ Alertes Slack absentes | ✅ Branche dédiée |
| ❌ Détecteur bounce/contact absent | ✅ Premier filtre avant parsing |
| ❌ Compteur soft cross-jours absent | ✅ Étape dédiée |
| ❌ Self-improving rules absent | ✅ Flèche pointillée LLM → Rules |
| ⚠️ Ordre logique inversé (boîte bounce après filtrage) | ✅ Flux corrigé : bounce **arrive** dans la BAL **puis** est filtré |
| ⚠️ Catégorie « unknown » absente | ✅ Branche `LLM pas confiant → unknown` |

---

## 📊 Schéma 1 — Architecture globale Cogiterra

> Vue infra : où s'insère notre serveur de filtrage entre le mail client, Postfix et Exchange.

```mermaid
flowchart LR
    MC[" Mail client externe"]:::ext

    subgraph COGI ["🏢 COGITERRA"]
        direction LR
        EX[" Serveur Exchange<br/>(BAL bounces + contacts)"]:::infra
        subgraph SRV ["🖥️ Serveur de filtrage mail"]
            direction TB
            PF[" Postfix<br/>(mode pipe)"]:::svc
            PY[" Pipeline Python<br/>Rules + LLM"]:::py
            DB[(" SQLite")]:::db
            DSH[" Dashboard<br/>Streamlit"]:::ui
        end
    end

    LLM[" Claude Haiku 4.5<br/>(fallback API)"]:::ai
    CMS[" CMS Cogiterra<br/>(webhook)"]:::out
    SLK[" Slack<br/>(alertes)"]:::alert
    CSV[" 3 CSV<br/>to_delete · to_pause · to_modify"]:::out

    MC -- "Bounce SMTP" --> PF
    MC -- "IMAP poll" --> EX
    EX -- "IMAP UNSEEN" --> PY
    PF -- "stdin" --> PY
    PY -- "confiance < 0.80" --> LLM
    LLM -- "catégorie + regex proposée" --> PY
    PY --> DB
    DB --> DSH
    PY -- "Rapport quotidien" --> CSV
    PY -- "POST JSON" --> CMS
    PY -- "Anomalie ?" --> SLK
    PY -- "Contact (faux bounce)" --> EX

    classDef ext fill:#1f2937,stroke:#475569,color:#e5e7eb,stroke-width:1.5px
    classDef infra fill:#1e3a8a,stroke:#60a5fa,color:#dbeafe,stroke-width:1.5px
    classDef svc fill:#312e81,stroke:#a78bfa,color:#ede9fe,stroke-width:1.5px
    classDef py fill:#4c1d95,stroke:#c4b5fd,color:#f3e8ff,stroke-width:1.5px
    classDef db fill:#064e3b,stroke:#34d399,color:#d1fae5,stroke-width:1.5px
    classDef ui fill:#7c2d12,stroke:#fb923c,color:#fed7aa,stroke-width:1.5px
    classDef ai fill:#831843,stroke:#f472b6,color:#fce7f3,stroke-width:1.5px
    classDef out fill:#78350f,stroke:#fbbf24,color:#fef3c7,stroke-width:1.5px
    classDef alert fill:#7f1d1d,stroke:#fb7185,color:#fecdd3,stroke-width:1.5px
```

---

## 🧩 Schéma 2 — Application interne (pipeline détaillé)

> Vue rapprochée des étages du pipeline Python, avec branchement Rules vs LLM.

```mermaid
flowchart LR
    IN[" Serveur Mail Cogiterra<br/>(Exchange)"]:::infra

    subgraph APP ["📦 Application Python"]
        direction TB
        DET[" Bounce Detector<br/>(bounce vs contact)"]:::py
        PRS[" Parser MIME + DSN<br/>(RFC 3464)"]:::py
        RUL{{" Rules Engine<br/>règles déterministes"}}:::rules
        LLM[" Claude Haiku 4.5<br/>fallback si conf < 0.80"]:::ai
        CNT[" Soft-bounce<br/>cross-jours"]:::py
        DB[(" SQLite<br/>5 tables")]:::db
        DSH[" Dashboard<br/>Streamlit 7 onglets"]:::ui
    end

    OUT1[" 3 CSV<br/>par email"]:::out
    OUT2[" Webhook CMS<br/>(POST JSON)"]:::out
    OUT3[" Alertes Slack<br/>(anomalies)"]:::alert
    FWD[" Forward BAL<br/>contact"]:::infra

    IN -- "IMAP poll<br/>ou Postfix pipe" --> DET
    DET -- "contact ?" --> FWD
    DET -- "bounce" --> PRS
    PRS --> RUL
    RUL -- "conf ≥ 0.80 (90%+ des cas)" --> CNT
    RUL -- "conf < 0.80" --> LLM
    LLM -- "catégorie + regex" --> CNT
    LLM -. "self-improving rules" .-> RUL
    CNT --> DB
    DB --> DSH
    DB -- "Rapport quotidien" --> OUT1
    DB --> OUT2
    DB --> OUT3

    classDef infra fill:#1e3a8a,stroke:#60a5fa,color:#dbeafe,stroke-width:1.5px
    classDef py fill:#4c1d95,stroke:#c4b5fd,color:#f3e8ff,stroke-width:1.5px
    classDef rules fill:#1e40af,stroke:#93c5fd,color:#dbeafe,stroke-width:1.5px
    classDef ai fill:#831843,stroke:#f472b6,color:#fce7f3,stroke-width:1.5px
    classDef db fill:#064e3b,stroke:#34d399,color:#d1fae5,stroke-width:1.5px
    classDef ui fill:#7c2d12,stroke:#fb923c,color:#fed7aa,stroke-width:1.5px
    classDef out fill:#78350f,stroke:#fbbf24,color:#fef3c7,stroke-width:1.5px
    classDef alert fill:#7f1d1d,stroke:#fb7185,color:#fecdd3,stroke-width:1.5px
```

---

## 🌳 Schéma 3 — Flowchart logique complet

> Tous les chemins de décision : du mail envoyé au CSV final.

```mermaid
flowchart TB
    A[" Envoi mail<br/>au client"]:::start
    B[" Réception<br/>fournisseur"]:::flow
    C{" Erreur SMTP ?"}:::decision
    D[" Bounce DSN<br/>retour expéditeur"]:::flow
    E[" Arrivée BAL bounces<br/>(Postfix ou IMAP)"]:::flow

    F{" Est-ce un bounce ?<br/>(détecteur)"}:::decision
    G[" Forward BAL<br/>contact"]:::out

    H[" Parser MIME + DSN<br/>extraction adresse,<br/>code, raison"]:::flow

    I{" Rules Engine<br/>confiance ≥ 0.80 ?"}:::decision
    J[" Catégorisation<br/>par règles"]:::flow
    K[" Appel<br/>Claude Haiku 4.5"]:::ai

    L{" LLM confiant ?"}:::decision
    M[" Catégorisation<br/>par LLM"]:::flow
    N[" Catégorie<br/>'unknown'"]:::warn
    O[" Suggestion regex<br/>→ rule_suggestions"]:::ai

    P[" Compteur<br/>soft cross-jours +1"]:::flow
    Q{" Catégorie ?"}:::decision
    R[" to_delete<br/>(hard bounce)"]:::out
    S[" to_pause<br/>(soft ≥ seuil)"]:::out
    T[" to_modify<br/>(changement adresse)"]:::out
    U[" Ignore<br/>(OOF, congé...)"]:::flow

    V[" SQLite<br/>(result + stats + counters)"]:::db
    W{" Anomalie ?<br/>pic / hard% / unknown%"}:::decision
    X[" 🚨 Alerte Slack"]:::alert
    Y[" Rapport quotidien<br/>3 CSV par email"]:::out
    Z[" Webhook CMS<br/>POST JSON"]:::out

    A --> B --> C
    C -- "Oui" --> D --> E
    C -- "Non (delivered)" --> END((" delivered")):::ok

    E --> F
    F -- "Non (contact)" --> G
    F -- "Oui (bounce)" --> H --> I
    I -- "Oui" --> J --> P
    I -- "Non" --> K --> L
    L -- "Oui" --> M --> O
    L -- "Non" --> N
    M --> P
    N --> P
    O -. "adoption dashboard" .-> I

    P --> Q
    Q --> R
    Q --> S
    Q --> T
    Q --> U
    R --> V
    S --> V
    T --> V
    U --> V

    V --> W
    W -- "Oui" --> X
    V --> Y
    V --> Z

    classDef start fill:#065f46,stroke:#34d399,color:#d1fae5,stroke-width:1.5px
    classDef flow fill:#1e293b,stroke:#94a3b8,color:#e5e7eb,stroke-width:1.5px
    classDef decision fill:#7c2d12,stroke:#fb923c,color:#fed7aa,stroke-width:1.5px
    classDef ai fill:#831843,stroke:#f472b6,color:#fce7f3,stroke-width:1.5px
    classDef out fill:#78350f,stroke:#fbbf24,color:#fef3c7,stroke-width:1.5px
    classDef db fill:#064e3b,stroke:#34d399,color:#d1fae5,stroke-width:1.5px
    classDef alert fill:#7f1d1d,stroke:#fb7185,color:#fecdd3,stroke-width:1.5px
    classDef warn fill:#713f12,stroke:#facc15,color:#fef9c3,stroke-width:1.5px
    classDef ok fill:#064e3b,stroke:#34d399,color:#d1fae5,stroke-width:1.5px
```

---

## 🛠️ Intégration rapide dans `index.html`

### Option A — En iframe (ultra simple)
```html
<iframe src="schemas.html"
        style="width:100%;height:100vh;border:0;border-radius:16px"></iframe>
```

### Option B — Copier/coller un bloc Mermaid
Dans le `<head>` (une seule fois) :
```html
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({ startOnLoad: true, theme: 'dark' });
</script>
```

Dans une slide :
```html
<section class="slide">
  <h2>Architecture</h2>
  <div class="mermaid">
    flowchart LR
      ...
  </div>
</section>
```

---

<sub>Cogiterra Bounces — H3 NIGHT INNOVATHON 2026</sub>
