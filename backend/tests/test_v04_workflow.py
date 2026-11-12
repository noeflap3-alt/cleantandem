"""Integration checks for the v0.4 browser-facing backend (local fictitious data)."""
import os
import sys
import tempfile
from pathlib import Path

# Import app after configuring an isolated database.
os.environ['CT_DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'v04.sqlite3')
os.environ['CT_DEV_ALLOW_INSECURE']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import app  # noqa:E402
from fastapi.testclient import TestClient


def test_app_static_routes_and_csrf_reload():
    with TestClient(app) as browser:
        home=browser.get('/')
        assert home.status_code==200 and 'CleanTandem' in home.text
        assert browser.get('/app.js').status_code==200
        assert browser.get('/styles.css').status_code==200
        assert browser.get('/api/clients').status_code==401
        create=browser.post('/auth/register',json={'email':'v04@example.test','password':'long-test-password-0','organization_name':'Fictive Company'})
        assert create.status_code==201
        old_csrf=create.json()['csrf_token']
        assert browser.get('/auth/me').status_code==200
        new_csrf=browser.get('/auth/csrf')
        assert new_csrf.status_code==200
        csrf=new_csrf.json()['csrf_token']
        assert csrf!=old_csrf
        assert browser.post('/api/clients',json={'payload':{'name':'Client Alpha'}},headers={'X-CSRF-Token':old_csrf}).status_code==403
        r=browser.post('/api/clients',json={'payload':{'name':'Client Alpha'}},headers={'X-CSRF-Token':csrf})
        assert r.status_code==201,r.text
        assert r.headers['cache-control']=='no-store'


def test_workflow_and_cross_client_site_rejected():
    with TestClient(app) as browser:
        auth=browser.post('/auth/register',json={'email':'workflow-v04@example.test','password':'long-test-password-1','organization_name':'Entreprise fictive B'})
        assert auth.status_code==201,auth.text
        headers={'X-CSRF-Token':auth.json()['csrf_token']}
        def add(kind,payload):return browser.post('/api/'+kind,json={'payload':payload},headers=headers)
        ca=add('clients',{'name':'Client A'});cb=add('clients',{'name':'Client B'})
        assert ca.status_code==cb.status_code==201
        c1=ca.json()['id'];c2=cb.json()['id']
        site=add('sites',{'name':'Site A','client_id':c1})
        assert site.status_code==201,site.text
        s1=site.json()['id']
        mismatched=add('quotes',{'title':'Mauvais devis','client_id':c2,'site_id':s1,
              'lines':[{'description':'A','quantity':1,'unit_price_cents':3000}]})
        assert mismatched.status_code==422,mismatched.text
        quotation=add('quotes',{'title':'Nettoyage bureaux','client_id':c1,'site_id':s1,'status':'brouillon',
                  'lines':[{'description':'Entretien bureaux','quantity':2,'unit_price_cents':9000}]})
        assert quotation.status_code==201,quotation.text
        quoteid=quotation.json()['id']
        updated=browser.patch('/api/quotes/'+quoteid,json={'payload':{'status':'accepté'}},headers=headers)
        assert updated.status_code==200 and updated.json()['status']=='accepté'
        job=add('jobs',{'title':'Passage du lundi','client_id':c1,'site_id':s1,'date':'2026-11-12','status':'prévue',
             'duration_minutes':120,'labor_rate_cents':1700,'supplies_cents':500,'travel_cents':1000,'revenue_cents':12000})
        assert job.status_code==201,job.text
        job_id=job.json()['id']
        assert browser.patch('/api/jobs/'+job_id,json={'payload':{'status':'réalisée'}},headers=headers).status_code==200
        assert browser.delete('/api/clients/'+c1,headers=headers).status_code==409
        assert browser.get('/api/jobs').json()[0]['status']=='réalisée'


def test_separate_organizations_block_each_other():
    with TestClient(app) as a, TestClient(app) as b:
        a1=a.post('/auth/register',json={'email':'org-a-v04@example.test','password':'very-long-password-A','organization_name':'Org A'})
        b1=b.post('/auth/register',json={'email':'org-b-v04@example.test','password':'very-long-password-B','organization_name':'Org B'})
        assert a1.status_code==b1.status_code==201
        c=a.post('/api/clients',json={'payload':{'name':'Confidentiel test'}},headers={'X-CSRF-Token':a1.json()['csrf_token']})
        assert c.status_code==201
        cid=c.json()['id']
        assert b.get('/api/clients').json()==[]
        assert b.patch('/api/clients/'+cid,json={'payload':{'name':'Intrusion'}},headers={'X-CSRF-Token':b1.json()['csrf_token']}).status_code==404
        assert b.delete('/api/clients/'+cid,headers={'X-CSRF-Token':b1.json()['csrf_token']}).status_code==404