"""Run on the VPS after staging acceptance. Additive migrations; no resets."""
import os
import pathlib
import shutil
import subprocess
import datetime
import psycopg

PROD=pathlib.Path('/var/www/product-hunter')
STAGE=pathlib.Path('/var/www/product-hunter-v2-test')
def database(path):
    return next(line.split('=',1)[1].strip() for line in pathlib.Path(path).read_text().splitlines() if line.startswith('DATABASE_URL='))

with psycopg.connect(database('/etc/product-hunter.env')) as conn:
    active=conn.execute("SELECT count(*) FROM research_runs WHERE status IN ('queued','running')").fetchone()[0]
    if active: raise SystemExit('Production research is active; drain before deployment')

stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
backup=pathlib.Path('/var/backups/product-hunter')
backup.mkdir(exist_ok=True,parents=True)
subprocess.run(['tar','--exclude=.venv','--exclude=.git','--exclude=__pycache__','-czf',str(backup/f'pre-v2-{stamp}.tgz'),'-C',str(PROD),'.'],check=True)
with (backup/f'pre-v2-{stamp}.dump').open('wb') as out:
    subprocess.run(['sudo','-u','postgres','pg_dump','-Fc','product_hunter'],stdout=out,check=True)
subprocess.run(['pm2','stop','demo-product-hunter-api','--silent'],check=True)
with psycopg.connect(database('/etc/product-hunter.env')) as conn:
    if conn.execute("SELECT count(*) FROM research_runs WHERE status IN ('queued','running')").fetchone()[0]:
        subprocess.run(['pm2','restart','demo-product-hunter-api','--silent'],check=True)
        raise SystemExit('A research started during backup; API restored, wait for completion')
subprocess.run(['pm2','stop','demo-product-hunter-worker','--silent'],check=True)
with psycopg.connect(database('/etc/product-hunter.env')) as conn:
    for name in ('008_generic_ontology.sql','009_generic_observed_clusters.sql','010_research_v2.sql','011_budget_adjustments.sql','012_structured_cache.sql'):
        conn.execute((STAGE/'backend/migrations'/name).read_text())
    # Test calls used the same provider account: preserve their spend against today's cap.
    with psycopg.connect(database('/etc/product-hunter-v2-test.env')) as test:
        costs=test.execute('SELECT created_at::date,SUM(COALESCE(cost,reserved)) FROM budget_calls GROUP BY 1').fetchall()
    for day,cost in costs:
        conn.execute("INSERT INTO budget_adjustments(source,day,cost) VALUES ('v2-acceptance',%s,%s) ON CONFLICT(source,day) DO UPDATE SET cost=EXCLUDED.cost",(day,cost))

for folder in ('backend','tests'):
    for path in (STAGE/folder).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc' or path.name=='app_v1.py': continue
        dest=PROD/path.relative_to(STAGE);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
for name in ('index.html','app.css','app-v2.js','v2.css','README.md','V2.md','ACCEPTANCE_V2.md','IMPLEMENTATION_PLAN.md'):
    shutil.copy2(STAGE/name,PROD/name)
for name in ('deploy-v2.py','rollback-v2.sh','live-acceptance.py'):
    shutil.copy2(STAGE/'scripts'/name,PROD/'scripts'/name)
subprocess.run([str(PROD/'.venv/bin/python'),'-m','compileall','-q','backend'],cwd=PROD,check=True)
subprocess.run(['pm2','restart','demo-product-hunter-api','demo-product-hunter-worker','--silent'],check=True)
print('Deployment completed. Rollback archive:',backup/f'pre-v2-{stamp}.tgz')
