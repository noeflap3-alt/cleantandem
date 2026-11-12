import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient


# Import only after the configured development database has been selected.
fp = Path(tempfile.mkdtemp()) / "test.sqlite3"
os.environ["CT_DATABASE_URL"] = "sqlite:///" + str(fp)
os.environ["CT_DEV_ALLOW_INSECURE"] = "1"
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app  # noqa: E402


def test_registration_sessions_tenant_isolation_and_csrf():
    with TestClient(app) as a, TestClient(app) as b:
        x=a.post('/auth/register',json={'email':'demo-a@example.test','password':'very-long-password-A','organization_name':'Entreprise A'})
        y=b.post('/auth/register',json={'email':'demo-b@example.test','password':'very-long-password-B','organization_name':'Entreprise B'})
        assert x.status_code==201, x.text
        assert y.status_code==201, y.text
        token_a=x.json()['csrf_token'];token_b=y.json()['csrf_token']
        d={'payload':{'name':'Client fictif Alpha','city':'Nice'}}
        assert a.post('/api/clients',json=d).status_code == 403  # must use CSRF header
        ca=a.post('/api/clients',json=d,headers={'X-CSRF-Token':token_a})
        assert ca.status_code == 201,ca.text
        cid=ca.json()['id']
        assert b.get('/api/clients').json()==[]
        assert a.get('/api/clients').json()[0]['name']=='Client fictif Alpha'
        assert b.patch(f'/api/clients/{cid}',json={'payload':{'name':'Pirated'}},headers={'X-CSRF-Token':token_b}).status_code==404
        assert b.delete(f'/api/clients/{cid}',headers={'X-CSRF-Token':token_b}).status_code==404
        assert a.post('/api/sites',json={'payload':{'name':'Site','client_id':'invalid'}},headers={'X-CSRF-Token':token_a}).status_code==404
        site=a.post('/api/sites',json={'payload':{'name':'Bureaux','client_id':cid}},headers={'X-CSRF-Token':token_a})
        assert site.status_code==201,site.text
        assert a.delete(f'/api/clients/{cid}',headers={'X-CSRF-Token':token_a}).status_code==409
        assert b.post('/api/jobs',json={'payload':{'title':'Test','client_id':cid}},headers={'X-CSRF-Token':token_b}).status_code==404
        lines=[{'description':'Nettoyage','quantity':3,'unit_price_cents':9900}]
        q=a.post('/api/quotes',json={'payload':{'title':'Devis Test','client_id':cid,'site_id':site.json()['id'],'lines':lines}},headers={'X-CSRF-Token':token_a})
        assert q.status_code==201,q.text
        assert a.get('/api/quotes').json()[0]['lines'][0]['unit_price_cents']==9900
        assert a.post('/auth/logout',headers={'X-CSRF-Token':token_a}).status_code==204
        assert a.get('/api/clients').status_code==401


def test_wrong_origin_is_rejected():
    with TestClient(app) as client:
        r=client.post('/auth/register',json={'email':'demo-c@example.test','password':'very-long-password-C','organization_name':'Entreprise C'})
        csrf=r.json()['csrf_token']
        assert client.post('/api/clients',json={'payload':{'name':'Demo'}},headers={'X-CSRF-Token':csrf,'Origin':'https://attacker.example'}).status_code==403


def test_no_unauthenticated_access():
    with TestClient(app) as client:
        assert client.get('/api/clients').status_code==401
        assert client.post('/api/clients',json={'payload':{'name':'Not allowed'}}).status_code==401