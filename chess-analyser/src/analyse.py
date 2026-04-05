from db import get_connection


def get_stats() -> dict:
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    if total == 0:
        conn.close()
        return {'total_games': 0}

    # ── Overall record ────────────────────────────────────────────────────────
    overall_rows = conn.execute(
        "SELECT outcome, COUNT(*) FROM games GROUP BY outcome"
    ).fetchall()
    overall = {row[0]: row[1] for row in overall_rows}

    # ── By colour ─────────────────────────────────────────────────────────────
    color_rows = conn.execute(
        "SELECT color, outcome, COUNT(*) FROM games GROUP BY color, outcome"
    ).fetchall()
    by_color = {'white': {}, 'black': {}}
    for color, outcome, count in color_rows:
        by_color[color][outcome] = count
    for color in by_color:
        t = sum(by_color[color].values())
        by_color[color]['total'] = t
        by_color[color]['win_rate'] = _pct(by_color[color].get('win', 0), t)

    # ── Top openings ──────────────────────────────────────────────────────────
    opening_rows = conn.execute('''
        SELECT opening_name,
               COUNT(*) AS total,
               SUM(outcome = 'win')  AS wins,
               SUM(outcome = 'loss') AS losses,
               SUM(outcome = 'draw') AS draws
        FROM games
        WHERE opening_name != 'Unknown' AND opening_name != ''
        GROUP BY opening_name
        ORDER BY total DESC
        LIMIT 12
    ''').fetchall()

    # ── Performance over time (monthly) ───────────────────────────────────────
    time_rows = conn.execute('''
        SELECT strftime('%Y-%m', datetime(date, 'unixepoch')) AS month,
               COUNT(*) AS total,
               SUM(outcome = 'win') AS wins
        FROM games
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    # ── By time control ───────────────────────────────────────────────────────
    tc_rows = conn.execute('''
        SELECT time_control,
               COUNT(*) AS total,
               SUM(outcome = 'win') AS wins
        FROM games
        GROUP BY time_control
        ORDER BY total DESC
    ''').fetchall()

    conn.close()

    return {
        'total_games': total,
        'overall': overall,
        'win_rate': _pct(overall.get('win', 0), total),
        'by_color': by_color,
        'top_openings': [
            {
                'name':     row[0],
                'total':    row[1],
                'wins':     row[2],
                'losses':   row[3],
                'draws':    row[4],
                'win_rate': _pct(row[2], row[1])
            }
            for row in opening_rows
        ],
        'over_time': [
            {
                'month':    row[0],
                'total':    row[1],
                'win_rate': _pct(row[2], row[1])
            }
            for row in time_rows
        ],
        'by_time_control': [
            {
                'control':  row[0],
                'total':    row[1],
                'win_rate': _pct(row[2], row[1])
            }
            for row in tc_rows
        ]
    }


def _pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0
