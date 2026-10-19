"""Read-only query state shared by manual requests and automations."""
import time

def snapshot(db,sources,automation=None):
    rows=sources.queries.status()
    automatic={r['request_id'] for r in db._rows('SELECT request_id FROM auto_node_queries WHERE request_id IS NOT NULL')} if automation else set()
    result=[dict(row,origin='automation' if row.get('request_id') in automatic else 'manual') for row in rows]
    overview=automation.overview() if automation else {}
    eligible=overview.get('pending_count',0) if overview.get('config',{}).get('enabled') else 0
    return {'success':True,'data':result,'eligible_total':eligible,'now_ms':int(time.time()*1000)}
