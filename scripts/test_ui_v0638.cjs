/* v0.6.38 Chromium regression: #155/#156 avisos, #157 favoritos, #158 balões, #159 presença. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8803','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8803/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],calls=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(route,body)=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  let notices=[];
  await page.route('**/api/devices/detected',r=>json(r,{success:true,data:notices}));
  for(const action of ['cancel','undo','dismiss','accept'])
   await page.route('**/api/devices/'+action,r=>{calls.push(action+':'+r.request().postData());return json(r,{success:true});});
  await page.route('**/api/nodes/favorite',r=>{calls.push('favorite:'+r.request().postData());return json(r,{success:true,status:'app_only'});});
  await page.goto('http://127.0.0.1:8803/mapa');
  await page.waitForFunction(()=>typeof renderDeviceNotices==='function'&&map!==null);
  const set=async list=>{notices=list;await page.evaluate(()=>refreshDeviceNotices());};
  const base={id:'b1',type:'detected',kind:'ble',address:'44:1B:F6:70:8A:69',name:'VHF4_8a68'};
  const out={};
  // #156: verificando com Cancelar e dica de PIN
  await set([{...base,job:{phase:'connecting',started_ms:Date.now()-5000}}]);
  out.connecting=await page.locator('#deviceNotices').innerText();
  await page.click('[data-notice-cancel="b1"]');
  // fila Bluetooth
  await set([{...base,job:{phase:'queued',position:2,total:4}}]);
  out.queued=await page.locator('#deviceNotices').innerText();
  // falha com Tentar de novo
  await set([{...base,job:{phase:'failed',error:'O rádio não respondeu a tempo pelo Bluetooth. Se ele pedir PIN…'}}]);
  out.failed=await page.locator('#deviceNotices').innerText();
  await page.click('[data-notice-add="b1"]');
  // #155: USB adicionado sozinho, com Desfazer
  await set([{id:'u1',type:'auto_added',kind:'serial',address:'COM11',name:'PT2VHF-6 - Tracker USB',switched:true}]);
  out.auto=await page.locator('#deviceNotices').innerText();
  await page.click('[data-notice-undo="u1"]');
  await set([]);
  const ui=await page.evaluate(async()=>{
   refreshAll=async()=>{};$('firstRunDialog')?.classList.remove('open');
   const r={},t=Date.now();
   nodes=[{node_num:0x11aa22bb,node_id:'!11aa22bb',long_name:'Renato_Kiid',short_name:'RK',favorite:false,
           presence:{state:'timeout',attempts:3,checked_ms:t-600000,reply_ms:0},last_seen_ms:t-5*3600000},
          {node_num:0x33cc44dd,node_id:'!33cc44dd',long_name:'Thiago Bressani',short_name:'TB',favorite:true,
           presence:{state:'replied',attempts:0,checked_ms:t-600000,reply_ms:t-600000},last_seen_ms:t-600000}];
   state.sources=[];state.connections={};
   // #158 balões
   await setView('messages');
   messages=[{id:1,direction:'rx',channel:0,to_node:4294967295,from_node:0x33cc44dd,text:'KZ50?',timestamp_ms:t-600000,state:'received'},
     {id:2,direction:'rx',channel:0,to_node:4294967295,from_node:0x11aa22bb,text:'↪ Thiago Bressani: KZ50?\nVai la agora.',timestamp_ms:t-500000,state:'received'},
     {id:3,direction:'rx',channel:0,to_node:4294967295,from_node:0x11aa22bb,text:'😂',timestamp_ms:t-480000,state:'received'},
     {id:4,direction:'tx',channel:0,to_node:4294967295,from_node:1,text:'Concordo',timestamp_ms:t-120000,state:'delivered'}];
   currentChat='channel:0';chatRenderSignature='';renderChat();
   const rows=[...document.querySelectorAll('#bubbles .msgRow')];
   r.heads=rows.map(x=>x.querySelector('.msgHead b')?.textContent||'');
   r.quote=rows[1].querySelector('.msgQuote')?.innerText;
   r.body=rows[1].querySelector('.bubble>div').innerText;
   r.grouped=rows[2].classList.contains('grouped');
   r.txAlign=getComputedStyle(rows[3]).alignSelf;
   r.pinned=$('contactPinned').innerText;
   currentChat='node:'+0x11aa22bb;chatRenderSignature='';renderChat();
   r.privateHeads=document.querySelectorAll('#bubbles .msgHead').length;
   // #157 favorito sem rádio + #159 presença
   await setView('nodes');selectedNodeCols.add('presence');renderNodes();
   r.presence=[...document.querySelectorAll('#nodesRows tr')].map(tr=>tr.innerText);
   r.starEnabled=!document.querySelector('[data-favorite-toggle="'+0x11aa22bb+'"]').disabled;
   document.querySelector('[data-favorite-toggle="'+0x11aa22bb+'"]').click();
   await new Promise(res=>setTimeout(res,300));
   r.dim=presenceSilent(nodes[0]);
   await setView('automations');await loadAutomation();
   r.kinds=[...document.querySelectorAll('[data-auto-kind]')].map(x=>x.dataset.autoKind);
   r.presenceFields=[$('autoPresenceSilent').value,$('autoPresenceWindow').value,$('autoChannelBusy').value];
   return r;
  });
  Object.assign(out,ui);
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1),calls);
  assert(out.connecting.includes('Verificando VHF4_8a68')&&out.connecting.includes('PIN')&&out.connecting.includes('Cancelar'));
  assert(calls.includes('cancel:{"id":"b1"}'));
  assert(out.queued.includes('2 de 4'));
  assert(out.failed.includes('Tentar de novo')&&out.failed.includes('não respondeu a tempo'));
  assert(calls.includes('accept:{"id":"b1"}'));
  assert(out.auto.includes('PT2VHF-6 - Tracker USB adicionado')&&out.auto.includes('rádio ativo')&&out.auto.includes('Desfazer'));
  assert(calls.includes('undo:{"id":"u1"}'));
  assert.deepEqual(out.heads,['Thiago Bressani','Renato_Kiid','','']);
  assert(out.quote.includes('Thiago Bressani')&&out.quote.includes('KZ50?'));
  assert.equal(out.body,'Vai la agora.');
  assert(out.grouped);assert.equal(out.txAlign,'flex-end');
  assert(out.pinned.includes('★ Favoritos'));
  assert.equal(out.privateHeads,0);
  assert(out.presence.some(x=>x.includes('sem resposta (3)'))&&out.presence.some(x=>x.includes('respondeu')));
  assert(out.starEnabled&&calls.some(c=>c.startsWith('favorite:{"node_num":'+0x11aa22bb+',"is_favorite":true')));
  assert(out.dim);
  assert(!out.kinds.includes('neighbors')&&out.kinds.includes('ping'));
  assert.deepEqual(out.presenceFields,['2','72','25']);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.38 OK',JSON.stringify(out).slice(0,300));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
