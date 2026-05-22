<?php
/**
 * Cogiterra Bounces — Dashboard PHP
 * Point d'entrée unique : route vers les vues selon ?tab=...
 *
 * Lancement : php -S localhost:8080 -t dashboard-php/
 *             → http://localhost:8080
 */
declare(strict_types=1);

require_once __DIR__ . '/config.php';
require_once __DIR__ . '/lib/db.php';
require_once __DIR__ . '/lib/helpers.php';
require_once __DIR__ . '/lib/actions.php';

$available = ['overview', 'today', 'surveillance', 'history', 'live', 'rules', 'data'];
$active = $_GET['tab'] ?? 'overview';
if (!in_array($active, $available, true)) $active = 'overview';

include __DIR__ . '/views/_layout_top.php';
include __DIR__ . '/views/' . $active . '.php';
include __DIR__ . '/views/_layout_bottom.php';
