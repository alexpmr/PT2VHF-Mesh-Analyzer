/* v0.6.46 Chromium regression (#190/#188): aba MeshCore, painel do nó, mapa e coleta periódica. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8809','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8809/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],posts=[];
  page.on('pageerror',e=>errors.push(String(e)+(process.env.MESH_DEBUG?e.stack:'')));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const idle={success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}};
  await page.route('**/api/devices/autoadd',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(idle)}));
  const json=(r,body)=>r.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  const overview={success:true,connected:true,source_id:1,
   automation:{config:{enabled:false,max_per_hour:6,min_gap_seconds:120,targets:[]},with_password:[],last:{reason:'Nada pendente'}},
   self:{name:'PT2VHF Base',public_key:'a1b2c3d4'+'00'.repeat(28),radio_freq:910.525,radio_bw:62.5,radio_sf:7,radio_cr:5,tx_power:20,manual_add_contacts:false},
   device:{max_contacts:100},contacts:3,by_type:{Repetidor:2,Companion:1},occupancy:{used:90,max:100,percent:90},hash_size:1,
   collisions:[{prefix:'0b',bytes:1,members:[{node_num:0x0badcafe,name:'Torre',type:'Repetidor'},{node_num:0x0b112233,name:'Morro',type:'Repetidor'}]}],
   paths:[{node_num:0x0badcafe,name:'Torre',type:'Repetidor',mode:'routed',hops:[{hash:'77',candidates:1,node_num:0x77665544,name:'Hub',latitude:-15.6,longitude:-47.8}],latitude:-15.7,longitude:-47.9},
          {node_num:0x55667788,name:'Maria',type:'Companion',mode:'flood',hops:[],latitude:null,longitude:null}],
   path_changes:[{timestamp_ms:Date.now(),node_num:0x0badcafe,name:'Torre',old_path:'',old_len:0,new_path:'77',new_len:1}],
   stale:[{node_num:0x55667788,name:'Maria',type:'Companion',last_advert:1700000000}],stale_days:30};
  await page.route('**/api/meshcore',r=>json(r,overview));
  await page.route('**/api/meshcore/results**',r=>json(r,{success:true,data:[{kind:'status',node_num:0x0badcafe,timestamp_ms:Date.now(),data:{bat:4100,noise_floor:-112}}]}));
  await page.route('**/api/meshcore/action',r=>{const b=JSON.parse(r.request().postData());posts.push(b);
   const data={channels:{channels:[{index:0,name:'Public',empty:false},{index:1,name:'',empty:true}]},status:{bat:4050,noise_floor:-110,uptime:7200},
     uri:{uri:'meshcore://abc'},advert:{flood:true}}[b.action]||{ok:true};return json(r,{success:true,data});});
  await page.route('**/api/meshcore/automation',r=>{posts.push({automation:JSON.parse(r.request().postData())});return json(r,{success:true,...overview.automation});});
  await page.goto('http://127.0.0.1:8809/estatisticas/meshcore');
  await page.waitForFunction(()=>typeof loadMeshcoreTab==='function'&&document.querySelector('#statsTabs'));
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();setView('stats');selectStatTab('meshcore');});
  await page.waitForFunction(()=>document.querySelector('#mcChannels')&&$('mcChannels').innerText.includes('Public'));
  const out={};
  out.tab=await page.evaluate(()=>({text:$('statsContents').innerText,autoAdd:$('mcAutoAdd2').checked}));
  await page.click('#mcAdvertFlood');await page.waitForFunction(()=>$('mcRadioOut').innerText.includes('toda a malha'));
  // Painel do nó MeshCore.
  out.node=await page.evaluate(async()=>{
   showNode({node_num:0x0badcafe,node_id:'!0badcafe',long_name:'Torre',hw_model:'MeshCore Repetidor',role:'REPEATER',last_seen_ms:Date.now()});
   for(let i=0;i<40&&!document.querySelector('[data-mc=status]');i++)await new Promise(r=>setTimeout(r,50));
   document.querySelector('[data-mc=status]').click();
   for(let i=0;i<40&&!$('mcNodeResult').innerText.includes('Ruído');i++)await new Promise(r=>setTimeout(r,50));
   const r={buttons:[...document.querySelectorAll('[data-mc]')].map(b=>b.dataset.mc),result:$('mcNodeResult').innerText,history:$('mcNodeHistory').innerText};
   closeNodeDetails();return r;
  });
  // Mapa: filtro de protocolo.
  out.map=await page.evaluate(()=>{
   const keep=nodes;nodes=[{node_num:1,hw_model:'MeshCore Repetidor'},{node_num:2,hw_model:'HELTEC_V3'}];
   const r={};for(const v of ['','meshcore','meshtastic']){$('mapProtocol').value=v;r[v||'all']=sourceMapNodes().map(n=>n.node_num);}
   $('mapProtocol').value='';nodes=keep;return r;
  });
  // Automações: bloco MeshCore.
  await page.evaluate(()=>setView('automations'));
  await page.waitForFunction(()=>$('mcAutoNode').options.length===2);
  out.auto=await page.evaluate(async()=>{
   const titles=[...document.querySelectorAll('#viewAutomations h3')].map(h=>h.innerText);
   $('mcAutoNode').value=String(0x0badcafe);$('mcAutoKind').value='status';$('mcAutoEvery').value='30';$('mcAutoPass').value='secreta';
   await $('mcAutoAdd').onclick();$('mcAutoEnabled').checked=true;await $('mcAutoSave').onclick();
   return {titles,rows:$('mcAutoTargets').innerText,results:$('mcAutoResults').innerText};
  });
  if(process.env.MESH_DEBUG)console.log(JSON.stringify({out,posts},null,1));
  assert(out.tab.text.includes('Colisões de prefixo')&&out.tab.text.includes('Torre')&&out.tab.text.includes('Morro'));
  assert(out.tab.text.includes('quase cheia')&&out.tab.text.includes('Maria')&&out.tab.text.includes('910,525 MHz'));
  assert(out.tab.autoAdd);
  assert(posts.some(p=>p.action==='advert'&&p.flood===true));
  assert.deepEqual(out.node.buttons,['telemetry','status','neighbours','trace','login','cli','discover','reset_path','remove']);
  assert(out.node.result.includes('Ruído -110 dBm')&&out.node.history.includes('Bateria 4,10 V'));
  assert(posts.some(p=>p.action==='status'&&p.node==='0xbadcafe'));
  assert.deepEqual(out.map,{all:[1,2],meshcore:[1],meshtastic:[2]});
  assert(out.auto.titles[0].startsWith('Meshtastic')&&out.auto.titles[1].startsWith('MeshCore')&&out.auto.titles[2].includes('Meshtastic e MeshCore'));
  assert(posts.some(p=>p.automation&&p.automation.password==='secreta'));
  const saved=posts.find(p=>p.automation&&p.automation.targets);
  assert.deepEqual(saved.automation.targets,[{node_num:0x0badcafe,kind:'status',interval_minutes:30}]);assert.equal(saved.automation.enabled,true);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.46 OK',JSON.stringify(out.map));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
