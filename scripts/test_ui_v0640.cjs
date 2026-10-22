/* v0.6.40 Chromium regression: idioma EN/ES (#176), alertas (#165), busca (#175),
   mensagens automáticas (#172/#173), canais (#174), análises (#167–#171), backup (#166) e PIN BLE (#164). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8805','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8805/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(route,body)=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/alerts',r=>json(r,{success:true,unread:1,alerts:[{id:7,kind:'battery',title:'Bateria baixa',text:'RPT1 com 12%',created_ms:Date.now(),read:false}]}));
  await page.route('**/api/messages/search?*',r=>json(r,{success:true,data:[{id:5,timestamp_ms:Date.now(),from_node:1,to_node:4294967295,channel:0,direction:'rx',text:'Bom dia pessoal'}]}));
  await page.route('**/api/channels',r=>json(r,{success:true,channels:[{index:0,name:'',role:'PRIMARY',encryption:'default'},{index:1,name:'Equipe',role:'SECONDARY',encryption:'custom'}]}));
  await page.route('**/api/insights/repeaters?*',r=>json(r,{success:true,data:{repeaters:[{node:9,name:'RPT1',role:'ROUTER',availability:95,last_seen_ms:Date.now(),battery:80,voltage:4.1,channel_util:12,air_util:2,route_hops:3,presence:'replied'}]}}));
  await page.goto('http://127.0.0.1:8805/mapa');
  await page.waitForFunction(()=>typeof applyLanguage==='function'&&map!==null);
  const out={};
  // #176: troca de idioma imediata, conteúdo dinâmico e volta ao português.
  out.lang=await page.evaluate(async()=>{
   const nav=()=>document.querySelector('.navbtn[data-view="map"]').textContent.trim();
   const r={pt:nav()};
   await setView('settings');showSettings('system');
   $('systemLanguage').value='en';$('systemLanguage').dispatchEvent(new Event('change'));
   r.en=nav();r.placeholder=$('messageSearch').placeholder;
   const d=document.createElement('button');d.textContent='Cancelar';document.body.appendChild(d);
   await new Promise(x=>setTimeout(x,30));r.dynamic=d.textContent;d.remove();
   notify('Configurações salvas');r.toast=$('toast').textContent;
   $('systemLanguage').value='es';$('systemLanguage').dispatchEvent(new Event('change'));r.es=nav();
   $('systemLanguage').value='pt';$('systemLanguage').dispatchEvent(new Event('change'));r.back=nav();r.backPlaceholder=$('messageSearch').placeholder;
   r.saved=(await api('/api/system/settings',{language:'en'})).settings.language;
   return r;
  });
  await page.reload();
  await page.waitForFunction(()=>typeof applyLanguage==='function'&&map!==null&&sysLoaded!==undefined);
  await page.evaluate(async()=>{await setView('settings');showSettings('system');});
  out.reload=await page.evaluate(()=>({lang:document.documentElement.lang,nav:document.querySelector('.navbtn[data-view="settings"]').textContent.trim(),select:$('systemLanguage').value}));
  out.invalid=await page.evaluate(async()=>{try{await api('/api/system/settings',{language:'fr'});return 'accepted';}catch(e){return 'rejected';}});
  await page.evaluate(async()=>{await api('/api/system/settings',{language:'pt'});applyLanguage('pt');await setView('map');});
  // #165: sino com contador e painel.
  out.alerts=await page.evaluate(async()=>{await refreshAlerts();const count=$('alertCount').textContent,hidden=$('alertCount').hidden;
   await openAlertPanel();const text=$('alertPanel').textContent;closeAlertPanel();return {count,hidden,panel:text.includes('Bateria baixa')};});
  // #175: busca no histórico.
  out.search=await page.evaluate(async()=>{await setView('messages');$('messageSearch').value='bom';await runMessageSearch();
   return {open:!$('messageSearchResults').hidden,mark:$('messageSearchResults').querySelector('mark')?.textContent};});
  // #174: canais secundários no seletor e no gerenciador.
  out.channels=await page.evaluate(async()=>{await refreshChannels();const opts=[...$('messageChannel').options].map(o=>o.textContent);
   await openChannelManager();const d=document.querySelector('dialog.messageContextDialog');const txt=d.textContent;d.querySelector('[data-chan-close]').click();
   return {opts:opts.slice(0,2),dialog:txt.includes('Equipe')&&!!d};});
  // #172/#173: cartão de mensagens automáticas.
  out.msgauto=await page.evaluate(async()=>{await setView('automations');await new Promise(r=>setTimeout(r,300));
   return document.body.textContent.includes('Respostas automáticas a comandos');});
  // #169: saúde dos repetidores; #168: gráfico.
  out.insights=await page.evaluate(async()=>{await setView('stats');selectStatTab('repetidores');
   for(let i=0;i<40&&!$('insightBox')?.querySelector('tr[data-insight-node]');i++)await new Promise(r=>setTimeout(r,50));
   return {rows:$('insightBox').querySelectorAll('tr[data-insight-node]').length,svg:sparkline([[1,2],[2,3]]).startsWith('<svg')};});
  // #166: cartão de backup.
  out.backup=await page.evaluate(()=>!!$('backupExport')&&!!$('backupRestoreFile'));
  // #164: campo de PIN no aviso BLE que falhou.
  out.pin=await page.evaluate(()=>{renderDeviceNotices([{id:'ble:AA',kind:'ble',address:'AA:BB:CC:DD:EE:FF',name:'Heltec',job:{phase:'failed',error:'Sem resposta',needs_pin:true}}]);
   return !!document.querySelector('[data-notice-pin-input="ble:AA"]')&&!!document.querySelector('[data-notice-pin="ble:AA"]');});
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1));
  assert.equal(out.lang.pt,'Mapa');assert.equal(out.lang.en,'Map');assert.equal(out.lang.es,'Mapa');
  assert.equal(out.lang.placeholder,'Search history…');assert.equal(out.lang.dynamic,'Cancel');assert.equal(out.lang.toast,'Settings saved');
  assert.equal(out.lang.back,'Mapa');assert.equal(out.lang.backPlaceholder,'Buscar no histórico…');assert.equal(out.lang.saved,'en');
  assert.deepEqual(out.reload,{lang:'en',nav:'Settings',select:'en'});
  assert.equal(out.invalid,'rejected');
  assert(out.alerts.count==='1'&&!out.alerts.hidden&&out.alerts.panel);
  assert(out.search.open&&/bom/i.test(out.search.mark||''));
  assert(out.channels.opts[1].includes('Equipe')&&out.channels.dialog);
  assert(out.msgauto);
  assert(out.insights.rows===1&&out.insights.svg);
  assert(out.backup&&out.pin);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.40 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
