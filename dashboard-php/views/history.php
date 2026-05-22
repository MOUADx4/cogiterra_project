<?php
/** Onglet historique 30j : stacked area + perf classifier */
declare(strict_types=1);

$history = history_30d();

$total_30d = 0;
$rules_30d = 0;
$llm_30d   = 0;
$conf_sum  = 0; $conf_n = 0;
foreach ($history as $h) {
    $total_30d += (int)$h['total_processed'];
    $rules_30d += (int)$h['n_by_rules'];
    $llm_30d   += (int)$h['n_by_llm'];
    if ($h['avg_confidence'] !== null) { $conf_sum += (float)$h['avg_confidence']; $conf_n++; }
}
$avg_conf = $conf_n ? round($conf_sum / $conf_n, 2) : 0;
$pct_rules_30d = $total_30d ? round($rules_30d / $total_30d * 100, 1) : 0;
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">30 derniers jours</div>
    <h1>Historique</h1>
  </div>
  <span class="muted"><?= count($history) ?> jours enregistrés</span>
</div>

<div class="grid-4 mb-4">
  <div class="bento" style="text-align:center;">
    <div class="kpi-mid gradient-text"><?= fr_int($total_30d) ?></div>
    <div class="kpi-label">Total 30 jours</div>
  </div>
  <div class="bento green" style="text-align:center;">
    <div class="kpi-mid" style="color:#34d399;"><?= fr_int($rules_30d) ?></div>
    <div class="kpi-label">Par règles</div>
  </div>
  <div class="bento violet" style="text-align:center;">
    <div class="kpi-mid" style="color:#c084fc;"><?= fr_int($llm_30d) ?></div>
    <div class="kpi-label">Par LLM</div>
  </div>
  <div class="bento blue" style="text-align:center;">
    <div class="kpi-mid" style="color:#60a5fa;"><?= number_format($avg_conf, 2) ?></div>
    <div class="kpi-label">Confiance moyenne</div>
  </div>
</div>

<div class="bento">
  <h3><span class="mi mi-blue">stacked_line_chart</span> Volumes par catégorie</h3>
  <?php if ($history): ?>
    <div class="chart" id="historyChart"></div>
  <?php else: ?>
    <div class="empty">
      <span class="mi">timeline</span>
      <p>Pas encore d'historique. Lance le mode <code>report</code> pour générer des stats.</p>
    </div>
  <?php endif; ?>
</div>

<?php if ($history): ?>
<div class="bento mt-4">
  <h3><span class="mi mi-violet">analytics</span> Performance classifier</h3>
  <p class="muted" style="font-size:0.85rem;">
    Part des bounces classés <strong>uniquement par règles</strong> sur les 30 derniers jours :
    <strong style="color:#34d399; font-size:1.1rem;"><?= fr_pct($pct_rules_30d) ?></strong>
  </p>
  <div class="bar" style="margin-top:14px;">
    <div class="bar-fill" style="width: <?= $pct_rules_30d ?>%; background:linear-gradient(90deg,#34d399,#60a5fa);"></div>
  </div>
  <p class="dim mt-3" style="font-size:0.78rem;">
    Plus la part « règles » augmente, plus le coût LLM diminue grâce au self-improving system.
  </p>
</div>
<?php endif; ?>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    <?php if ($history): ?>
      chartHistory('historyChart', <?= json_encode($history, JSON_UNESCAPED_UNICODE) ?>);
    <?php endif; ?>
  });
</script>
