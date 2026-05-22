<?php
/**
 * Configuration globale du dashboard PHP.
 * Centralise tous les chemins relatifs à la racine du projet.
 */
declare(strict_types=1);

// Racine du projet (un niveau au-dessus de dashboard-php)
define('PROJECT_ROOT', dirname(__DIR__));
define('DB_PATH', PROJECT_ROOT . '/data/bounces.db');
define('USER_RULES_PATH', PROJECT_ROOT . '/data/user_rules.json');
define('PYTHON_BIN', PROJECT_ROOT . '/venv/bin/python');
define('MAIN_SCRIPT', PROJECT_ROOT . '/main.py');

// Charge .env si présent (lecture simple, sans dépendance)
$envPath = PROJECT_ROOT . '/.env';
if (file_exists($envPath)) {
    foreach (file($envPath, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        if (str_starts_with(trim($line), '#')) continue;
        if (!str_contains($line, '=')) continue;
        [$k, $v] = array_map('trim', explode('=', $line, 2));
        $v = trim($v, "\"' ");
        if (!isset($_ENV[$k])) $_ENV[$k] = $v;
    }
}

// Seuils & constantes (équivalents au config.py Python)
define('SOFT_BOUNCE_THRESHOLD', (int)($_ENV['SOFT_BOUNCE_THRESHOLD'] ?? 5));
define('SOFT_BOUNCE_WARNING',   (int)($_ENV['SOFT_BOUNCE_WARNING']   ?? 3));
define('COST_PER_EMAIL_CENTS', 0.05);

// Catégories : labels et couleurs (cohérent avec Streamlit)
const CATEGORY_LABELS = [
    'hard_bounce'     => 'Hard bounce',
    'soft_bounce'     => 'Soft bounce',
    'address_change'  => 'Changement',
    'technical_error' => 'Technique',
    'unknown'         => 'Non classifié',
];
const CATEGORY_COLORS = [
    'hard_bounce'     => '#ef4444',
    'soft_bounce'     => '#f59e0b',
    'address_change'  => '#3b82f6',
    'technical_error' => '#a855f7',
    'unknown'         => '#64748b',
];

// Helper : retourne le label affichable d'une catégorie
function category_label(string $cat): string {
    return CATEGORY_LABELS[$cat] ?? $cat;
}
function category_color(string $cat): string {
    return CATEGORY_COLORS[$cat] ?? '#64748b';
}
