<?php
/** Onglet surveillance : soft bounces cross-jours */
declare(strict_types=1);

$tracked = soft_tracking();

$zones = ['OK' => 0, 'Surveillance' => 0, 'Alerte' => 0, 'Critique' => 0];
foreach ($tracked as $t) {
    [$lbl] = soft_zone((int)$t['failures']);
    $zones[$lbl] = ($zones[$lbl] ?? 0) + 1;
}
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">Soft bounces cross-jours</div>
    <h1>Surveillance</h1>
  </div>
  <div class="row gap-3">
    <a href="api/export_csv.php?type=soft" class="btn">
      <span class="mi">download</span><span>Export CSV</span>
    </a>
  </div>
</div>

<div class="grid-4 mb-4">
  <div class="bento green" style="text-align:center;">
    <div class="kpi-mid" style="color:#34d399;"><?= $zones['OK'] ?? 0 ?></div>
    <div class="kpi-label">OK (&lt; 1)</div>
  </div>
  <div class="bento blue" style="text-align:center;">
    <div class="kpi-mid" style="color:#60a5fa;"><?= $zones['Surveillance'] ?? 0 ?></div>
    <div class="kpi-label">Surveillance</div>
  </div>
  <div class="bento amber" style="text-align:center;">
    <div class="kpi-mid" style="color:#fbbf24;"><?= $zones['Alerte'] ?? 0 ?></div>
    <div class="kpi-label">Alerte (≥ <?= SOFT_BOUNCE_WARNING ?>)</div>
  </div>
  <div class="bento danger" style="text-align:center;">
    <div class="kpi-mid" style="color:#f87171;"><?= $zones['Critique'] ?? 0 ?></div>
    <div class="kpi-label">Critique (≥ <?= SOFT_BOUNCE_THRESHOLD ?>)</div>
  </div>
</div>

<div class="bento">
  <h3><span class="mi mi-amber">visibility</span> Adresses sous surveillance</h3>
  <p class="muted mt-2" style="font-size:0.85rem;">
    Le compteur est <strong>cross-jours</strong> : il s'incrémente à chaque soft bounce et
    se vide après bascule en <code>to_pause</code> (seuil = <?= SOFT_BOUNCE_THRESHOLD ?>).
  </p>

  <div class="table-wrap mt-3">
    <table class="data">
      <thead>
        <tr>
          <th>Email</th>
          <th>Échecs</th>
          <th>Zone</th>
          <th>Dernière occurrence</th>
        </tr>
      </thead>
      <tbody>
        <?php if (empty($tracked)): ?>
          <tr><td colspan="4" class="center muted" style="padding:40px;">
            <span class="mi" style="font-size:36px;opacity:0.4;">verified</span>
            <p>Aucune adresse sous surveillance.</p>
          </td></tr>
        <?php else: foreach ($tracked as $t):
          [$zlbl, $zcls] = soft_zone((int)$t['failures']);
        ?>
          <tr>
            <td class="mono"><?= h($t['email_address']) ?></td>
            <td><strong><?= h((string)$t['failures']) ?></strong> / <?= SOFT_BOUNCE_THRESHOLD ?></td>
            <td><span class="badge <?= $zcls ?>"><?= h($zlbl) ?></span></td>
            <td class="font-mono"><?= h(fr_dt($t['last_failure'])) ?></td>
          </tr>
        <?php endforeach; endif; ?>
      </tbody>
    </table>
  </div>
</div>
