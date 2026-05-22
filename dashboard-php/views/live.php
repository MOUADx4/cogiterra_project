<?php
/** Activité live : feed temps réel (refresh JS toutes les 5s) */
declare(strict_types=1);

$rows = live_activity(20);
?>
<div class="page-head">
  <div>
    <div class="breadcrumb">Feed temps réel</div>
    <h1>Activité live</h1>
  </div>
  <span class="row gap-2"><span class="pulse"></span>Rafraîchissement auto · 5s</span>
</div>

<div class="bento">
  <h3><span class="mi mi-green">bolt</span> 20 derniers traitements</h3>
  <p class="muted" style="font-size:0.85rem;">
    Le feed se met à jour automatiquement. Pas besoin de recharger la page.
  </p>

  <div id="liveFeed" class="mt-3">
    <?php if (empty($rows)): ?>
      <div class="empty">
        <span class="mi">hourglass_empty</span>
        <p>En attente d'activité…</p>
      </div>
    <?php else: foreach ($rows as $r): ?>
      <div class="suggestion" style="margin-bottom:8px;">
        <div>
          <div class="row gap-2">
            <span class="mono"><?= h($r['email_address']) ?></span>
            <span class="badge <?= category_badge_class($r['category']) ?>"><?= h(category_label($r['category'])) ?></span>
          </div>
          <div class="sample"><?= h(truncate((string)($r['reason'] ?? ''), 100)) ?></div>
        </div>
        <div class="dim font-mono"><?= h(fr_dt($r['processed_at'])) ?></div>
      </div>
    <?php endforeach; endif; ?>
  </div>
</div>
