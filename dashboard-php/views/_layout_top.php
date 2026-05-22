<?php
/** Partial : haut de page commun (HTML head + sidebar) */
declare(strict_types=1);

$active = $active ?? 'overview';
$tabs = [
    'overview'     => ['Vue d\'ensemble',  'dashboard'],
    'today'        => ['Aujourd\'hui',     'today'],
    'surveillance' => ['Surveillance',     'visibility'],
    'history'      => ['Historique 30j',   'trending_up'],
    'live'         => ['Activité live',    'bolt'],
    'rules'        => ['Règles suggérées', 'smart_toy'],
    'data'         => ['Données',          'database'],
];

$today = function_exists('today_stats') ? today_stats() : [];
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cogiterra Bounces · Operations</title>
<link rel="icon" href="assets/cogiterra_logo.png">
<link rel="stylesheet" href="assets/style.css">
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
</head>
<body>
<div class="layout">
  <!-- ============== Sidebar ============== -->
  <aside class="sidebar">
    <div class="sidebar-logo">
      <img src="assets/cogiterra_logo.png" alt="Cogiterra">
      <div>
        <div class="name">Cogiterra</div>
        <div class="sub">BOUNCES · OPS</div>
      </div>
    </div>

    <div class="sidebar-section">Navigation</div>
    <nav>
      <?php foreach ($tabs as $k => [$lbl, $icon]): ?>
        <a class="nav-item <?= $active === $k ? 'active' : '' ?>" href="?tab=<?= $k ?>">
          <span class="mi"><?= $icon ?></span>
          <span><?= h($lbl) ?></span>
        </a>
      <?php endforeach; ?>
    </nav>

    <div class="sidebar-section">Stats live</div>
    <div class="sidebar-stat">
      <div class="label">Total aujourd'hui</div>
      <div class="val gradient-text"><?= fr_int($today['total'] ?? 0) ?></div>
    </div>
    <div class="sidebar-stat">
      <div class="label">Surveillance</div>
      <div class="val" style="color:#fbbf24;"><?= fr_int($today['n_tracked'] ?? 0) ?></div>
    </div>
    <div class="sidebar-stat">
      <div class="label">Hard bounces</div>
      <div class="val" style="color:#f87171;"><?= fr_int($today['n_hard'] ?? 0) ?></div>
    </div>

    <div class="sidebar-section">Actions</div>
    <button class="sidebar-btn" onclick="actionPoll(this)">
      <span class="mi">cloud_download</span><span>Lancer poll IMAP</span>
    </button>
    <button class="sidebar-btn warn" onclick="actionReport(this)">
      <span class="mi">send</span><span>Générer rapport</span>
    </button>
    <button class="sidebar-btn demo" onclick="actionDemo(this)">
      <span class="mi">auto_awesome</span><span>Injecter données démo</span>
    </button>

    <div class="sidebar-section">Système</div>
    <div style="font-size:0.78rem; color:var(--dim); line-height:1.6;">
      <div><span class="pulse"></span> Pipeline opérationnel</div>
      <div class="mt-2">Dashboard <span class="mono">PHP</span> · v1.0</div>
      <div>SQLite · <?= file_exists(DB_PATH) ? '✓ connectée' : '✗ absente' ?></div>
    </div>
  </aside>

  <!-- ============== Main ============== -->
  <main class="main">
