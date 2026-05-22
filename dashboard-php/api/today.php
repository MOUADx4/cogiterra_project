<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/db.php';
header('Content-Type: application/json; charset=utf-8');

$rows = fetch_results([
    'category' => $_GET['category'] ?? 'all',
    'method'   => $_GET['method']   ?? 'all',
    'search'   => $_GET['search']   ?? '',
    'limit'    => 500,
]);
echo json_encode(['rows' => $rows], JSON_UNESCAPED_UNICODE);
