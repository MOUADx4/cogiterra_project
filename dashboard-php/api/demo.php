<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/actions.php';
header('Content-Type: application/json; charset=utf-8');

try {
    inject_demo_data();
    echo json_encode(['ok' => true]);
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
}
