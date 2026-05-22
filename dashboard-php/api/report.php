<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/actions.php';
header('Content-Type: application/json; charset=utf-8');

[$code, $output] = run_main_mode('report');
echo json_encode(['code' => $code, 'output' => $output], JSON_UNESCAPED_UNICODE);
