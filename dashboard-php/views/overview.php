<?php
/** Vue d'ensemble : KPIs + donut + méthodes + top domaines + health score */
declare(strict_types=1);

$today    = today_stats();
$total    = $today['total'];
$pct_rules = $total ? round($today['n_rules'] / $total * 100, 1) : 0;
$pct_class = $total ? round(($total - $today['n_unknown']) / $total * 100, 1) : 0;
$score    = compute_health_score($today, ['n_warning' => $today['n_warning']]);
[$health_lbl, $health_color] = health_label($score);

$distrib = [
    'hard_bounce'     => $today['n_hard'],
    'soft_bounce'     => $today['n_soft'],
    'address_change'  => $today['n_changes'],
    'technical_error' => $today['n_technical'],
    'unknown'         => $today['n_unknown'],
];
$distrib = array_filter($distrib, fn($v) => $v > 0);
$domains = top_domains(10);
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">Operations · <?= date('d/m/Y') ?></div>
    <h1>Vue d'ensemble</h1>
  </div>
  <div class="row gap-3">
    <span class="badge badge-ok"><span class="pulse"></span>Système en production</span>
  </div>
</div>

<!-- KPIs principaux -->
<div class="grid-4 mb-4">
  <div class="bento">
    <div class="kpi-big gradient-text"><?= fr_int($total) ?></div>
    <div class="kpi-label">Total traité</div>
  </div>
  <div class="bento blue">
    <div class="kpi-big" style="color:#60a5fa;"><?= fr_pct($pct_class) ?></div>
    <div class="kpi-label">Classification</div>
  </div>
  <div class="bento green">
    <div class="kpi-big gradient-green"><?= fr_pct($pct_rules) ?></div>
    <div class="kpi-label">Par règles</div>
  </div>
  <div class="bento amber">
    <div class="kpi-big" style="color:#fbbf24;"><?= fr_int($today['n_above']) ?></div>
    <div class="kpi-label">Au-dessus seuil</div>
  </div>
</div>

<!-- Donut + Health -->
<div class="grid-2 mb-4">
  <div class="bento">
    <h3><span class="mi mi-blue">donut_large</span> Distribution des catégories</h3>
    <div class="chart" id="donutChart"></div>
  </div>
  <div class="bento green">
    <h3><span class="mi mi-green">monitor_heart</span> Email Health Score</h3>
    <div class="gauge" id="healthGauge"></div>
    <div class="center mt-3">
      <span class="badge <?= health_label($score)[2] ?>"><?= h($health_lbl) ?></span>
    </div>
    <p class="muted center mt-3" style="font-size:0.85rem;">
      Score calculé sur le ratio hard, les non-classifiés et la surveillance.
    </p>
  </div>
</div>

<!-- Méthodes + Top domaines -->
<div class="grid-2">
  <div class="bento violet">
    <h3><span class="mi mi-violet">tune</span> Règles vs LLM</h3>
    <div class="chart" id="methodsChart" style="min-height:260px;"></div>
    <p class="muted mt-3" style="font-size:0.85rem;">
      <strong style="color:#60a5fa;"><?= fr_int($today['n_rules']) ?></strong> par règles ·
      <strong style="color:#c084fc;"><?= fr_int($today['n_llm']) ?></strong> par LLM ·
      confiance moy. LLM : <strong><?= number_format($today['avg_confidence'], 2) ?></strong>
    </p>
  </div>
  <div class="bento blue">
    <h3><span class="mi mi-blue">domain</span> Top 10 domaines</h3>
    <?php if ($domains): ?>
      <div class="chart" id="domainsChart"></div>
    <?php else: ?>
      <div class="empty">
        <span class="mi">inbox</span>
        <p>Aucune donnée pour le moment.</p>
      </div>
    <?php endif; ?>
  </div>
</div>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    chartDonut('donutChart', <?= json_encode($distrib, JSON_UNESCAPED_UNICODE) ?>);
    chartMethods('methodsChart', <?= json_encode($today, JSON_UNESCAPED_UNICODE) ?>);
    <?php if ($domains): ?>
      chartDomains('domainsChart', <?= json_encode($domains, JSON_UNESCAPED_UNICODE) ?>);
    <?php endif; ?>
    renderGauge(<?= $score ?>);
  });
</script>
