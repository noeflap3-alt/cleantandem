"""Tenant boundaries and HTML escaping for newly added v0.5 features."""
import os
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient

os.environ['CT_DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'v05.sqlite3')
os.environ['CT_DEV_ALLOW_INSECURE']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app  # noqa:E402


def test_export_is_private_and_print_is_tenant_scoped():
    with TestClient(app) as a, TestClient(app) as b:
        assert a.get('/api/export').status_code == 401
        assert a.get('/api/quotes/xxx/print').status_code == 401
        ra=a.post('/auth/register',json={'email':'export-a@example.test','password':'long-synthetic-password-a','organization_name':'Démo A'})
        rb=b.post('/auth/register',json={'email':'export-b@example.test','password':'long-synthetic-password-b','organization_name':'Démo B'})
        assert ra.status_code == rb.status_code == 201
        ha={'X-CSRF-Token':ra.json()['csrf_token']}
        hb={'X-CSRF-Token':rb.json()['csrf_token']}
        c=a.post('/api/clients',headers=ha,json={'payload':{'name':'Client & <script>alert(1)</script>'}})
        assert c.status_code == 201
        cid=c.json()['id']
        s=a.post('/api/sites',headers=ha,json={'payload':{'name':'Bureaux & site','client_id':cid}})
        assert s.status_code == 201
        quote=a.post('/api/quotes',headers=ha,json={'payload':{
            'title':'Nettoyage <img src=x onerror=alert(1)>','client_id':cid,'site_id':s.json()['id'],
            'lines':[{'description':'Vitres & sols','quantity':2,'unit_price_cents':4900}]}})
        assert quote.status_code == 201
        qid=quote.json()['id']
        snapshot=a.get('/api/export')
        assert snapshot.status_code==200
        assert snapshot.headers['content-disposition'].startswith('attachment;')
        assert snapshot.headers['cache-control']=='no-store' or 'no-store' in snapshot.headers['cache-control']
        data=snapshot.json()
        assert data['resources']['clients'][0]['id']==cid
        assert data['resources']['quotes'][0]['id']==qid
        assert b.get('/api/export').json()['resources']['clients']==[]
        assert b.get(f'/api/quotes/{qid}/print').status_code==404
        printed=a.get(f'/api/quotes/{qid}/print')
        assert printed.status_code==200
        assert 'DOCUMENT FICTIF' in printed.text
        assert '98,00 €' in printed.text
        assert '&lt;script&gt;alert(1)&lt;/script&gt;' in printed.text
        assert '<script>alert(1)</script>' not in printed.text
        assert '&lt;img src=x onerror=alert(1)&gt;' in printed.text
        assert printed.headers.get('content-security-policy')
        assert b.post('/api/clients',headers=hb,json={'payload':{'name':'Entreprise de démonstration B'}}).status_code==201
        assert len(b.get('/api/export').json()['resources']['clients'])==1
        assert len(a.get('/api/export').json()['resources']['clients'])==1