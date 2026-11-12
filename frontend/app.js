(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const state = { authMode:'login', view:'home', csrf:null, me:null, data:{clients:[],sites:[],quotes:[],jobs:[]}, form:null, quoteSource:null, lines:[{description:'',quantity:1,unit_price_cents:10000}] };
  const H = v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const euros = c => (Number(c||0)/100).toLocaleString('fr-FR',{style:'currency',currency:'EUR'});
  const cents = s => { const n=Number(String(s).replace(',','.'));return Number.isFinite(n)&&n>=0&&n<1000000?Math.round(n*100):NaN; };
  const dollars = n => String((Number(n||0)/100).toFixed(2));
  const nameFor=(kind,id)=>state.data[kind].find(x=>x.id===id)?.name || '—';
  const toast=(msg,isError=false)=>{const el=$('toast');el.textContent=msg;el.style.background=isError?'#9a3d31':'';el.classList.add('show');clearTimeout(window._toastTimeout);window._toastTimeout=setTimeout(()=>el.classList.remove('show'),4500);};
  async function api(path,opts={}){
    const o={credentials:'same-origin',headers:{Accept:'application/json',...(opts.body?{'Content-Type':'application/json'}:{}),...(opts.method&&opts.method!=='GET'&&state.csrf?{'X-CSRF-Token':state.csrf}:{}),...(opts.headers||{})},...opts};
    let res;try{res=await fetch(path,o);}catch(e){throw new Error("Le service est momentanément indisponible. Réessaie plus tard ou contacte CleanTandem.");}
    if(res.status===204)return null;
    let data;try{data=await res.json();}catch{throw new Error('Réponse du serveur invalide.');}
    if(!res.ok){if(res.status===401&& !path.startsWith('/auth')){showAuth();}const det=data?.detail;throw new Error(typeof det==='string'?det:res.status===409?'Conflit détecté':`Erreur ${res.status}`);}
    return data;
  }
  function showAuth(){state.me=null;state.csrf=null;state.authMode='login';$('auth-title').textContent='Connexion';$('org-wrap').classList.add('hidden');$('invite-wrap').classList.add('hidden');$('auth-submit').textContent='Se connecter';$('auth-toggle').textContent='Créer un compte de test';$('shell').classList.add('hidden');$('auth').classList.remove('hidden');}
  async function showApp(){const me=await api('/auth/me');state.me=me;const csrf=await api('/auth/csrf');state.csrf=csrf.csrf_token;$('auth').classList.add('hidden');$('shell').classList.remove('hidden');$('org-name').textContent='Entreprise de démonstration';$('user-email').textContent=me.email;await refresh();}
  async function refresh(){try{const [clients,sites,quotes,jobs]=await Promise.all(['clients','sites','quotes','jobs'].map(k=>api('/api/'+k)));state.data={clients,sites,quotes,jobs};render();}catch(e){toast(e.message,true);}}
  const readonly = () => state.view === 'home';
  const buttons = (kind)=> `<div class="toolbar"><h2>${({clients:'Clients',sites:'Sites',quotes:'Devis',jobs:'Interventions'})[kind]}</h2><button class="btn primary" data-add="${kind}">+ Ajouter</button></div>`;
  const badge=t=>`<span class="badge ${t==='accepté'||t==='réalisée'?'':'warn'}">${H(t||'brouillon')}</span>`;
  const moneySum=q=>(q.lines||[]).reduce((sum,l)=>sum+(Number(l.quantity)||0)*(Number(l.unit_price_cents)||0),0);
  const jobCost=j=>Math.round((j.duration_minutes||0)*(j.labor_rate_cents||0)/60)+(j.supplies_cents||0)+(j.travel_cents||0);
  function dashboard(){
    const {clients,sites,quotes,jobs}=state.data;
    const accepted=quotes.filter(x=>x.status==='accepté').reduce((a,q)=>a+moneySum(q),0);
    const revenue=jobs.reduce((a,j)=>a+(j.revenue_cents||0),0),cost=jobs.reduce((a,j)=>a+jobCost(j),0);
    const signed=quotes.filter(x=>x.status==='accepté').length;
    return `<div class="cards"><div class="card"><span class="card-label">Entreprises clientes</span><div class="metric">${clients.length}</div><span class="subtle">Espace de test</span></div>
      <div class="card"><span class="card-label">Sites</span><div class="metric">${sites.length}</div><span class="subtle">Chantiers suivis</span></div>
      <div class="card"><span class="card-label">Devis acceptés</span><div class="metric">${signed}</div><span class="subtle">${euros(accepted)} HT</span></div>
      <div class="card"><span class="card-label">Interventions</span><div class="metric">${jobs.length}</div><span class="subtle">${jobs.filter(j=>j.status==='réalisée').length} réalisées</span></div></div>
      <div class="grid-two"><div class="panel"><h2>Rentabilité opérationnelle prévisionnelle</h2><p class="muted">Une estimation des coûts directs des interventions saisies.</p>
       <div class="sumline"><span>Recettes HT</span><strong>${euros(revenue)}</strong></div>
       <div class="sumline"><span>Coûts directs</span><strong>${euros(cost)}</strong></div>
       <div class="sumline"><span>Marge directe</span><strong>${euros(revenue-cost)}</strong></div>
       <div class="progress"><div style="width:${Math.max(0,Math.min(100,revenue>0?(revenue-cost)*100/revenue:0))}%"></div></div><p class="subtle">Hors abonnements du logiciel, charges fixes, impôts et autres frais.</p></div>
       <div class="panel"><h2>Parcours à tester</h2><p class="muted">1. Créer un client fictif<br/>2. Ajouter son site<br/>3. Préparer un devis<br/>4. Planifier une intervention<br/>5. Mesurer la marge</p><button class="btn primary" data-view="clients">Commencer par un client</button><p><button class="btn secondary" id="export-demo">Exporter les données (JSON)</button></p><p class="subtle">Les données de test sont enregistrées dans la base locale du serveur, et non dans le navigateur.</p></div></div>`;
  }
  const table=(heads,rows)=>rows.length?`<div class="panel table-scroll"><table><thead><tr>${heads.map(x=>`<th>${H(x)}</th>`).join('')}<th>Actions</th></tr></thead><tbody>${rows.join('')}</tbody></table></div>`:'<div class="panel empty">Aucun élément. Clique sur « + Ajouter » pour commencer.</div>';
  const action=(kind,id,extra='')=>`<div class="row-actions">${extra}<button class="btn danger" data-delete="${kind}" data-id="${H(id)}" aria-label="Supprimer">Supprimer</button></div>`;
  const clientsView=()=>buttons('clients')+table(['Entreprise','Ville','Email'],state.data.clients.map(c=>`<tr><td><strong>${H(c.name)}</strong></td><td>${H(c.city||'—')}</td><td>${H(c.email||'—')}</td><td>${action('clients',c.id)}</td></tr>`));
  const sitesView=()=>buttons('sites')+table(['Site','Client','Ville'],state.data.sites.map(s=>`<tr><td><strong>${H(s.name)}</strong></td><td>${H(nameFor('clients',s.client_id))}</td><td>${H(s.city||'—')}</td><td>${action('sites',s.id)}</td></tr>`));
  const quotesView=()=>buttons('quotes')+table(['Devis','Client','Prestations','Total HT','Statut'],state.data.quotes.map(q=>`<tr><td><strong>${H(q.title)}</strong></td><td>${H(nameFor('clients',q.client_id))}</td><td>${(q.lines||[]).length} ligne(s)</td><td><strong>${euros(moneySum(q))}</strong></td><td>${badge(q.status)}</td><td>${action('quotes',q.id,`${q.status==='accepté'?`<button class="btn primary" data-plan-quote="${H(q.id)}">Planifier</button>`:''}<button class="btn secondary" data-print="${H(q.id)}">Aperçu imprimable</button><button class="btn secondary" data-accept="${H(q.id)}">${q.status==='accepté'?'Rep. brouillon':'Accepter'}</button>`)}</td></tr>`));
  const jobsView=()=>buttons('jobs')+table(['Intervention','Site','Date','Recettes','Marge directe','Statut'],state.data.jobs.slice().sort((a,b)=>String(a.date).localeCompare(String(b.date))).map(j=>`<tr><td><strong>${H(j.title)}</strong></td><td>${H(nameFor('sites',j.site_id))}</td><td>${H(j.date)}</td><td>${euros(j.revenue_cents)}</td><td><strong>${euros((j.revenue_cents||0)-jobCost(j))}</strong></td><td>${badge(j.status)}</td><td>${action('jobs',j.id,`<button class="btn secondary" data-complete="${H(j.id)}">${j.status==='réalisée'?'Replanifier':'Terminer'}</button>`)}</td></tr>`));
  function options(kind,selected){return state.data[kind].map(x=>`<option value="${H(x.id)}" ${x.id===selected?'selected':''}>${H(x.name)}</option>`).join('');}
  const formStart=title=>`<section class="panel"><div class="toolbar"><h2>${title}</h2><button class="btn" data-cancel="1">Fermer</button></div><form id="record-form" class="form">`;
  const field=(id,label,kind='text',value='',extra='')=>`<div class="field"><label for="${id}">${label}</label><input id="${id}" name="${id}" type="${kind}" value="${H(value)}" ${extra}/></div>`;
  function renderForm(){const kind=state.form;if(!kind)return '';
    const clients=state.data.clients, sites=state.data.sites;
    const source=kind==='jobs'?state.quoteSource:null;
    if(kind!=='clients'&&clients.length===0)return `<div class="alert">Ajoute d'abord un client fictif avant de créer un site, devis ou une intervention.</div>`;
    let s=formStart(({clients:'Ajouter un client',sites:'Ajouter un site',quotes:'Nouveau devis',jobs:'Planifier une intervention'})[kind]);
    if(kind==='clients')s+=field('name','Nom de l’entreprise fictive','text','', 'required minlength="2"')+field('city','Ville')+`<div class="field full"><label for="email-contact">Email fictif facultatif</label><input id="email-contact" name="contact_email" type="email" placeholder="demo@example.test"/></div>`;
    else {s+=`<div class="field"><label for="client_id">Entreprise</label><select id="client_id" name="client_id" required>${options('clients',source?.client_id)}</select></div>`;
    if(kind==='sites')s+=field('name','Nom du site','text','', 'required')+field('city','Ville');
    else {
      s+=`<div class="field"><label for="site_id">Site</label><select id="site_id" name="site_id" required><option value="">Choisir un site</option>${state.data.sites.filter(x=>x.client_id===(source?.client_id||clients[0]?.id)).map(x=>`<option value="${H(x.id)}" ${x.id===source?.site_id?'selected':''}>${H(x.name)}</option>`).join('')}</select></div>`;
      if(kind==='quotes'){
        s+=field('title','Intitulé du devis','text','', 'required');
        s+=`<div class="form-notice">Prestations détaillées : quantités et prix HT. Les montants sont enregistrés en centimes pour éviter les erreurs d'arrondi.</div>`;
        s+=`<div class="field full"><label>Prestations</label><div id="quote-lines">${state.lines.map((line,i)=>`<div class="grid-two" style="margin-bottom:10px"><div class="field"><label>Description ${i+1}</label><input name="line_desc_${i}" value="${H(line.description)}" placeholder="Nettoyage bureaux" required/></div><div class="grid-two"><div class="field"><label>Quantité</label><input name="line_qty_${i}" value="${H(line.quantity)}" type="number" min="1" step="1" required/></div><div class="field"><label>PU HT (€)</label><input name="line_price_${i}" value="${dollars(line.unit_price_cents)}" type="number" min="0" step="0.01" required/></div></div></div>`).join('')}</div><button type="button" id="add-line" class="btn secondary">+ Ajouter une prestation</button></div>`;
      } else {
        const today=new Date().toISOString().slice(0,10);
        s+=field('title','Prestation / intervention','text',source?.title||'', 'required')+field('date','Date','date',today,'required');
        s+=field('duration','Durée prévue (heures)','number','2','min="0.25" step="0.25" required')+field('hourly','Coût horaire chargé (€)','number','17','min="0" step="0.01" required')+field('supplies','Consommables (€)','number','5','min="0" step="0.01"')+field('travel','Déplacement (€)','number','10','min="0" step="0.01"')+field('revenue','Recette HT prévue (€)','number',source?dollars(moneySum(source)):'120','min="0" step="0.01" required');
      }
    }}
    return s+`<div class="form-actions"><button class="btn" type="button" data-cancel="1">Annuler</button><button class="btn primary" type="submit">Enregistrer</button></div></form></section>`;
  }
  const descriptions={home:['Tableau de bord','Clients, devis, interventions et rentabilité réunis au même endroit.'],clients:['Clients','Centralise la liste des entreprises clientes.'],sites:['Sites de nettoyage','Associe les bâtiments et chantiers aux entreprises clientes.'],quotes:['Devis','Prépare tes chiffrages et suis leur acceptation.'],jobs:['Planning et interventions','Programme les passages et visualise leur marge directe.']};
  function render(){if(!state.me)return;document.querySelectorAll('#menu .nav-item').forEach(b=>b.classList.toggle('active',b.dataset.view===state.view));
    $('view-title').textContent=descriptions[state.view][0];$('view-desc').textContent=descriptions[state.view][1];
    $('content').innerHTML=renderForm()+({home:dashboard,clients:clientsView,sites:sitesView,quotes:quotesView,jobs:jobsView})[state.view]();
  }
  function storeLineDraft(){if(state.form!=='quotes')return;state.lines=state.lines.map((l,i)=>{const f=$('record-form');if(!f)return l;return {description:f.elements.namedItem('line_desc_'+i)?.value||'',quantity:Number(f.elements.namedItem('line_qty_'+i)?.value)||1,unit_price_cents:cents(f.elements.namedItem('line_price_'+i)?.value)||0};});}
  async function submitForm(form){let kind=state.form;let fd=new FormData(form);let payload={};
    if(kind==='clients')payload={name:String(fd.get('name')||'').trim(),city:String(fd.get('city')||'').trim(),email:String(fd.get('contact_email')||'').trim()};
    else {
      payload.client_id=String(fd.get('client_id')||'');
      if(kind==='sites')payload={...payload,name:String(fd.get('name')||'').trim(),city:String(fd.get('city')||'').trim()};
      else {
        payload.site_id=String(fd.get('site_id')||'');payload.title=String(fd.get('title')||'').trim();
        if(!payload.site_id)throw new Error('Crée ou sélectionne un site pour continuer.');
        let site=state.data.sites.find(x=>x.id===payload.site_id);
        if(!site||site.client_id!==payload.client_id)throw new Error('Le site choisi doit appartenir au client sélectionné.');
        if(kind==='quotes'){
          payload.status='brouillon';payload.lines=state.lines.map((l,i)=>({description:String(fd.get('line_desc_'+i)||'').trim(),quantity:Number(fd.get('line_qty_'+i)),unit_price_cents:cents(fd.get('line_price_'+i))}));
          if(payload.lines.some(l=>!l.description||!Number.isInteger(l.quantity)||l.quantity<=0||!Number.isInteger(l.unit_price_cents)))throw new Error('Vérifie les lignes de devis.');
        }else{
          const hours=Number(fd.get('duration'));payload.duration_minutes=Math.round(hours*60);
          payload.labor_rate_cents=cents(fd.get('hourly'));
          payload.supplies_cents=cents(fd.get('supplies'));payload.travel_cents=cents(fd.get('travel'));payload.revenue_cents=cents(fd.get('revenue'));payload.date=String(fd.get('date')||'');payload.status='prévue';
          if(!Number.isFinite(hours)||hours<=0||[payload.labor_rate_cents,payload.supplies_cents,payload.travel_cents,payload.revenue_cents].some(n=>!Number.isInteger(n)))throw new Error('Vérifie la durée et les montants.');
        }
      }
    }
    await api('/api/'+kind,{method:'POST',body:JSON.stringify({payload})});state.form=null;state.lines=[{description:'',quantity:1,unit_price_cents:10000}];toast('Données de test enregistrées.');await refresh();
  }
  document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
    if(b.dataset.view){state.view=b.dataset.view;state.form=null;render();return;}
    if(b.dataset.add){state.quoteSource=null;state.form=b.dataset.add;state.lines=[{description:'',quantity:1,unit_price_cents:10000}];render();return;}
    if(b.dataset.cancel){state.form=null;render();return;}
    if(b.id==='add-line'){storeLineDraft();if(state.lines.length>=12)return toast('12 prestations maximum pour cette démo.',true);state.lines.push({description:'',quantity:1,unit_price_cents:5000});render();return;}
    if(b.id==='export-demo'){
      try{
        const res=await fetch('/api/export',{credentials:'same-origin',headers:{Accept:'application/json'}});
        if(!res.ok)throw new Error('Impossible d’exporter les données.');
        const blob=await res.blob();const u=URL.createObjectURL(blob);const link=document.createElement('a');link.href=u;link.download='cleantandem-export-demo.json';document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(u),30000);
        toast('Export de test téléchargé.');
      }catch(err){toast(err.message,true);}
      return;
    }
    if(b.dataset.planQuote){const q=state.data.quotes.find(x=>x.id===b.dataset.planQuote);if(!q||q.status!=='accepté')return;state.quoteSource=q;state.form='jobs';state.view='jobs';render();toast('Devis repris. Vérifie la date, la durée et les coûts avant de sauvegarder.');return;}
    if(b.dataset.print){window.open('/api/quotes/'+encodeURIComponent(b.dataset.print)+'/print','_blank','noopener');return;}
    if(b.dataset.delete){if(!confirm('Supprimer cet élément fictif ?'))return;try{await api(`/api/${b.dataset.delete}/${b.dataset.id}`,{method:'DELETE'});toast('Élément supprimé.');await refresh();}catch(err){toast(err.message,true);}return;}
    if(b.dataset.accept){const q=state.data.quotes.find(x=>x.id===b.dataset.accept);if(!q)return;try{await api('/api/quotes/'+q.id,{method:'PATCH',body:JSON.stringify({payload:{status:q.status==='accepté'?'brouillon':'accepté'}})});await refresh();}catch(err){toast(err.message,true);}return;}
    if(b.dataset.complete){const j=state.data.jobs.find(x=>x.id===b.dataset.complete);if(!j)return;try{await api('/api/jobs/'+j.id,{method:'PATCH',body:JSON.stringify({payload:{status:j.status==='réalisée'?'prévue':'réalisée'}})});await refresh();}catch(err){toast(err.message,true);}return;}
  });
  document.addEventListener('change',e=>{if(e.target.id!=='client_id')return;const select=$('site_id');if(!select)return;select.innerHTML='<option value="">Choisir un site</option>'+state.data.sites.filter(x=>x.client_id===e.target.value).map(x=>`<option value="${H(x.id)}">${H(x.name)}</option>`).join('');});
  document.addEventListener('submit',async e=>{if(e.target?.id!=='record-form')return;e.preventDefault();const btn=e.target.querySelector('[type="submit"]');btn.disabled=true;try{await submitForm(e.target);}catch(err){toast(err.message,true);}finally{btn.disabled=false;}});
  $('auth-toggle').addEventListener('click',()=>{state.authMode=state.authMode==='login'?'register':'login';$('auth-title').textContent=state.authMode==='register'?'Créer un espace de test':'Connexion';$('org-wrap').classList.toggle('hidden',state.authMode!=='register');$('invite-wrap').classList.toggle('hidden',state.authMode!=='register');$('auth-submit').textContent=state.authMode==='register'?'Créer mon espace de test':'Se connecter';$('auth-toggle').textContent=state.authMode==='register'?'J’ai déjà un compte':'Créer un compte de test';$('auth-error').textContent='';});
  $('auth-form').addEventListener('submit',async e=>{e.preventDefault();$('auth-error').textContent='';const body={email:$('email').value,password:$('password').value};if(state.authMode==='register'){body.organization_name=$('org').value;body.invitation_code=$('invitation').value;}
    $('auth-submit').disabled=true;try{const r=await api(state.authMode==='register'?'/auth/register':'/auth/login',{method:'POST',body:JSON.stringify(body)});state.csrf=r.csrf_token;await showApp();}catch(err){$('auth-error').textContent=err.message;}finally{$('auth-submit').disabled=false;}
  });
  $('logout').addEventListener('click',async()=>{try{await api('/auth/logout',{method:'POST'});}catch(e){toast(e.message,true);}showAuth();});
  (async()=>{try{await showApp();}catch{showAuth();}})();
})();