<?php
/** Onglet données : exploration brute SQLite */
declare(strict_types=1);

$tables = ['result', 'stats', 'soft_bounce_counter', 'counters', 'rule_suggestions'];
$selected = $_GET['t'] ?? 'result';
if (!in_array($selected, $tables, true)) $selected = 'result';

$counts = [];
foreach ($tables as $t) {
    $counts[$t] = table_exists($t)
        ? (int)db()->query("SELECT COUNT(*) FROM $t")->fetchColumn()
        : 0;
}

$rows = [];
$cols = [];
if (table_exists($selected)) {
    $st = db()->query("SELECT * FROM $selected LIMIT 100");
    $rows = $st->fetchAll();
    if ($rows) $cols = array_keys($rows[0]);
}
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">SQLite · <?= h(basename(DB_PATH)) ?></div>
    <h1>Données</h1>
  </div>
</div>

<div class="grid-4 mb-4">
  <?php foreach (['result' => 'Bounces du jour', 'stats' => 'Stats par jour', 'soft_bounce_counter' => 'Compteur soft', 'rule_suggestions' => 'Suggestions règles'] as $t => $lbl): ?>
    <a href="?tab=data&t=<?= $t ?>" class="bento <?= $selected === $t ? 'blue' : '' ?>" style="text-decoration:none;color:inherit;">
      <div class="kpi-mid"><?= fr_int($counts[$t] ?? 0) ?></div>
      <div class="kpi-label"><?= h($lbl) ?></div>
      <div class="muted mt-2" style="font-size:0.78rem;"><code><?= h($t) ?></code></div>
    </a>
  <?php endforeach; ?>
</div>

<div class="bento">
  <div class="between">
    <h3><span class="mi">database</span> Table <code><?= h($selected) ?></code></h3>
    <span class="muted">100 premières lignes</span>
  </div>

  <?php if (empty($rows)): ?>
    <div class="empty">
      <span class="mi">inbox</span>
      <p>Table vide ou absente.</p>
    </div>
  <?php else: ?>
    <div class="table-wrap mt-3" style="overflow-x:auto;">
      <table class="data">
        <thead>
          <tr><?php foreach ($cols as $c): ?><th><?= h($c) ?></th><?php endforeach; ?></tr>
        </thead>
        <tbody>
          <?php foreach ($rows as $r): ?>
            <tr>
              <?php foreach ($cols as $c):
                $v = $r[$c] ?? '';
                $isNum = is_numeric($v) && !is_string($v);
              ?>
                <td <?= $isNum ? 'class="font-mono"' : '' ?>><?= h(is_scalar($v) ? (string)$v : json_encode($v)) ?></td>
              <?php endforeach; ?>
            </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>
  <?php endif; ?>
</div>
