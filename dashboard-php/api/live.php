<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/db.php';
header('Content-Type: application/json; charset=utf-8');

echo json_encode(['rows' => live_activity(20)], JSON_UNESCAPED_UNICODE);
