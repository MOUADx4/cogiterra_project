<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/actions.php';
header('Content-Type: application/json; charset=utf-8');

$body = json_decode(file_get_contents('php://input') ?: '[]', true) ?: [];
$id = (int)($body['id'] ?? 0);
if ($id <= 0) {
    http_response_code(400);
    echo json_encode(['ok' => false]);
    exit;
}
reject_suggestion($id);
echo json_encode(['ok' => true]);
