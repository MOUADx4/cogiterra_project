<?php
/** Onglet règles suggérées : adopter / rejeter */
declare(strict_types=1);

$pending  = rule_suggestions('pending');
$adopted  = rule_suggestions('adopted');
$rejected = rule_suggestions('rejected');
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">Self-improving rules</div>
    <h1>Règles suggérées</h1>
  </div>
  <a href="api/export_csv.php?type=rules" class="btn">
    <span class="mi">download</span><span>Export CSV</span>
  </a>
</div>

<div class="grid-3 mb-4">
  <div class="bento amber" style="text-align:center;">
    <div class="kpi-mid" style="color:#fbbf24;"><?= count($pending) ?></div>
    <div class="kpi-label">En attente</div>
  </div>
  <div class="bento green" style="text-align:center;">
    <div class="kpi-mid" style="color:#34d399;"><?= count($adopted) ?></div>
    <div class="kpi-label">Adoptées</div>
  </div>
  <div class="bento" style="text-align:center;">
    <div class="kpi-mid" style="color:#94a3b8;"><?= count($rejected) ?></div>
    <div class="kpi-label">Rejetées</div>
  </div>
</div>

<div class="bento violet">
  <h3><span class="mi mi-violet">smart_toy</span> Suggestions en attente</h3>
  <p class="muted" style="font-size:0.85rem;">
    Patterns regex proposés par le LLM. Adopter une suggestion l'ajoute à <code>user_rules.json</code>
    et évite de rappeler le LLM pour des bounces similaires.
  </p>

  <div class="mt-3">
    <?php if (empty($pending)): ?>
      <div class="empty">
        <span class="mi">verified</span>
        <p>Aucune suggestion en attente.</p>
      </div>
    <?php else: foreach ($pending as $s): ?>
      <div class="suggestion">
        <div>
          <div class="row gap-2">
            <span class="pattern"><?= h($s['pattern']) ?></span>
            <span class="badge <?= category_badge_class($s['category']) ?>"><?= h(category_label($s['category'])) ?></span>
            <span class="muted" style="font-size:0.8rem;">conf. <?= number_format((float)$s['confidence'], 2) ?></span>
          </div>
          <div class="sample mt-2"><strong style="color:#94a3b8;">Exemple</strong> · <?= h(truncate((string)($s['sample_text'] ?? ''), 160)) ?></div>
          <div class="muted mt-2" style="font-size:0.82rem;"><strong>Raison LLM</strong> : <?= h($s['llm_reason']) ?></div>
          <div class="dim font-mono mt-2"><?= h(fr_dt($s['suggested_at'])) ?></div>
        </div>
        <div class="actions">
          <button class="btn btn-ok" onclick="adoptRule(<?= (int)$s['id'] ?>, this)">
            <span class="mi">check</span><span>Adopter</span>
          </button>
          <button class="btn btn-danger" onclick="rejectRule(<?= (int)$s['id'] ?>, this)">
            <span class="mi">close</span><span>Rejeter</span>
          </button>
        </div>
      </div>
    <?php endforeach; endif; ?>
  </div>
</div>

<?php if ($adopted): ?>
<div class="bento green mt-4">
  <h3><span class="mi mi-green">check_circle</span> Adoptées (<?= count($adopted) ?>)</h3>
  <div class="table-wrap mt-2">
    <table class="data">
      <thead>
        <tr><th>Pattern</th><th>Catégorie</th><th>Adoptée le</th></tr>
      </thead>
      <tbody>
        <?php foreach ($adopted as $a): ?>
          <tr>
            <td class="mono"><?= h($a['pattern']) ?></td>
            <td><span class="badge <?= category_badge_class($a['category']) ?>"><?= h(category_label($a['category'])) ?></span></td>
            <td class="font-mono"><?= h(fr_dt($a['decided_at'] ?? $a['suggested_at'])) ?></td>
          </tr>
        <?php endforeach; ?>
      </tbody>
    </table>
  </div>
</div>
<?php endif; ?>
