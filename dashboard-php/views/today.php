<?php
/** Onglet aujourd'hui : table filtrable + export CSV */
declare(strict_types=1);

$rows = fetch_results(['limit' => 500]);
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">Bounces du jour · <?= date('d/m/Y') ?></div>
    <h1>Aujourd'hui</h1>
  </div>
  <a href="api/export_csv.php?type=today" class="btn btn-primary">
    <span class="mi">download</span>
    <span>Exporter CSV</span>
  </a>
</div>

<div class="bento">
  <div class="filters">
    <label>Catégorie</label>
    <select id="fltCat">
      <option value="all">Toutes</option>
      <option value="hard_bounce">Hard bounce</option>
      <option value="soft_bounce">Soft bounce</option>
      <option value="address_change">Changement</option>
      <option value="technical_error">Technique</option>
      <option value="unknown">Non classifié</option>
    </select>

    <label>Méthode</label>
    <select id="fltMethod">
      <option value="all">Toutes</option>
      <option value="rules">Règles</option>
      <option value="llm">LLM</option>
    </select>

    <label>Recherche</label>
    <input type="search" id="fltSearch" placeholder="email ou raison…" style="min-width:280px;">

    <span class="muted" style="margin-left:auto;">
      <strong id="todayCount"><?= count($rows) ?></strong> ligne(s)
    </span>
  </div>

  <div class="table-wrap">
    <table class="data" id="todayTable">
      <thead>
        <tr>
          <th>Email</th>
          <th>Catégorie</th>
          <th>Confiance</th>
          <th>Méthode</th>
          <th>Raison</th>
          <th>Traité</th>
        </tr>
      </thead>
      <tbody>
        <?php if (empty($rows)): ?>
          <tr><td colspan="6" class="center muted" style="padding:40px;">
            Aucun bounce traité aujourd'hui. <br><span class="dim">Lance un poll IMAP ou injecte des données démo.</span>
          </td></tr>
        <?php else: foreach ($rows as $r): ?>
          <tr>
            <td class="mono"><?= h($r['email_address']) ?></td>
            <td><span class="badge <?= category_badge_class($r['category']) ?>"><?= h(category_label($r['category'])) ?></span></td>
            <td><?= $r['confidence'] !== null ? number_format((float)$r['confidence'], 2) : '—' ?></td>
            <td><?= h($r['method']) ?></td>
            <td class="muted"><?= h(truncate((string)($r['reason'] ?? ''), 60)) ?></td>
            <td class="font-mono"><?= h(fr_dt($r['processed_at'])) ?></td>
          </tr>
        <?php endforeach; endif; ?>
      </tbody>
    </table>
  </div>
</div>
