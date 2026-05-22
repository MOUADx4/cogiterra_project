<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/actions.php';
header('Content-Type: application/json; charset=utf-8');

$body = json_decode(file_get_contents('php://input') ?: '[]', true) ?: [];
$id = (int)($body['id'] ?? 0);
if ($id <= 0) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'id manquant']);
    exit;
}

// Récupère la suggestion pour avoir les champs
$st = db()->prepare("SELECT * FROM rule_suggestions WHERE id = ?");
$st->execute([$id]);
$row = $st->fetch();
if (!$row) {
    http_response_code(404);
    echo json_encode(['ok' => false, 'error' => 'introuvable']);
    exit;
}

$ok = adopt_suggestion(
    $id,
    (string)$row['pattern'],
    (string)$row['category'],
    (float)($row['confidence'] ?? 0.85),
    (string)($row['llm_reason'] ?? '')
);

echo json_encode(['ok' => $ok]);
