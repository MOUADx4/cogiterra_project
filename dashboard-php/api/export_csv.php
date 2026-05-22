<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/db.php';
require_once __DIR__ . '/../lib/helpers.php';

$type = $_GET['type'] ?? 'today';
$filename = 'cogiterra_' . $type . '_' . date('Y-m-d') . '.csv';

header('Content-Type: text/csv; charset=utf-8');
header('Content-Disposition: attachment; filename="' . $filename . '"');

if ($type === 'soft') {
    $rows = soft_tracking();
    echo csv_from_rows($rows, ['email_address', 'failures', 'last_failure']);
} elseif ($type === 'rules') {
    $rows = rule_suggestions('pending');
    echo csv_from_rows($rows, ['id', 'pattern', 'category', 'confidence', 'sample_email', 'suggested_at']);
} else {
    $rows = fetch_results([
        'category' => $_GET['category'] ?? 'all',
        'method'   => $_GET['method']   ?? 'all',
        'search'   => $_GET['search']   ?? '',
    ]);
    echo csv_from_rows($rows, [
        'email_address', 'category', 'confidence', 'new_email',
        'reason', 'method', 'processed_at'
    ]);
}
