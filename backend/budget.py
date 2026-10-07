"""Atomic reservations shared by search and structured model calls.

Unknown costs retain their reservation (conservative estimate), including restart.
Provider-side overruns cannot be undone; no new calls start once the cap is hit.
"""
import os
from decimal import Decimal
from backend.db import connect

class BudgetBlocked(RuntimeError):
    pass

def reserve(run_id, kind, amount='0.04'):
    policy = os.getenv('PRODUCT_HUNTER_EXTERNAL_CALLS', 'all')
    if policy not in ('all', 'model_only', 'off'):
        raise BudgetBlocked('Неизвестная настройка внешних вызовов; запросы остановлены')
    if policy == 'off' or (policy == 'model_only' and kind in ('market', 'supplier')):
        raise BudgetBlocked('Режим разработки: новые платные запросы поиска отключены' if policy == 'model_only' else 'Режим разработки: внешние платные запросы отключены')
    amount = Decimal(amount)
    with connect() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(7348201)')
        run = conn.execute('SELECT status,budget_usd FROM research_runs WHERE id=%s FOR UPDATE', (run_id,)).fetchone()
        if not run or run['status'] not in ('running','queued'):
            raise BudgetBlocked('Исследование остановлено')
        spent = conn.execute('SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) AS n FROM budget_calls WHERE run_id=%s', (run_id,)).fetchone()['n']
        development_cap = os.getenv('PRODUCT_HUNTER_DEVELOPMENT_TOTAL_BUDGET_USD')
        if development_cap is not None:
            total = conn.execute('SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) AS n FROM budget_calls').fetchone()['n']
            if total + amount > Decimal(development_cap):
                raise BudgetBlocked('Достигнут общий бюджет разработки; сохранён частичный результат')
        day = conn.execute("""SELECT
            (SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM budget_calls WHERE created_at>=date_trunc('day',now())) +
            (SELECT COALESCE(SUM(cost),0) FROM budget_adjustments WHERE day=current_date) +
            (SELECT COALESCE(SUM(actual_cost_usd),0) FROM research_runs WHERE pipeline_version=1 AND created_at>=date_trunc('day',now())) AS n""").fetchone()['n']
        if spent + amount > run['budget_usd'] or day + amount > Decimal(os.getenv('PRODUCT_HUNTER_DAILY_LIVE_BUDGET_USD','3.00')):
            raise BudgetBlocked('Достигнут лимит расходов; сохранён частичный результат')
        return conn.execute('INSERT INTO budget_calls(run_id,kind,reserved) VALUES (%s,%s,%s) RETURNING id', (run_id,kind,amount)).fetchone()['id']

def settle(call_id, cost=None):
    with connect() as conn:
        row = conn.execute("UPDATE budget_calls SET cost=%s,state=%s WHERE id=%s RETURNING run_id", (cost,'settled' if cost is not None else 'estimated',call_id)).fetchone()
        conn.execute("""UPDATE research_runs SET
            ontology_cost_usd=(SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM budget_calls WHERE run_id=%s AND kind='ontology'),
            clustering_cost_usd=(SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM budget_calls WHERE run_id=%s AND kind='clustering')
            WHERE id=%s""",(row['run_id'],row['run_id'],row['run_id']))
    refresh(row['run_id'])

def refresh(run_id):
    with connect() as conn:
        row = conn.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) AS total, COUNT(*) FILTER (WHERE cost IS NULL) AS uncertain FROM budget_calls WHERE run_id=%s", (run_id,)).fetchone()
        conn.execute('UPDATE research_runs SET actual_cost_usd=%s,estimated_cost_usd=%s WHERE id=%s AND pipeline_version=2', (row['total'],row['total'],run_id))
        return float(row['total']), int(row['uncertain'])

def warning(run_id, message):
    from psycopg.types.json import Jsonb
    with connect() as conn:
        conn.execute("UPDATE research_runs SET warnings=CASE WHEN warnings @> %s THEN warnings ELSE warnings || %s END WHERE id=%s", (Jsonb([message]),Jsonb([message]),run_id))
