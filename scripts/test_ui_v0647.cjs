/* v0.6.47 Chromium regression (#189): escolher no topo a conexão (rádio ou MQTT) cujos dados aparecem. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8810','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8810/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(r,body)=>r.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}}));
  // Um rádio USB conectado (26) e um MQTT conectado (28), como no relato.
  await page.route('**/api/state',async r=>{
   const real=await (await r.fetch()).json();
   real.sources=[{id:26,name:'PT2VHF-4 - Móvel',kind:'serial',enabled:true,config:{port:'COM5'}},
                 {id:28,name:'Platorm',kind:'mqtt',enabled:true,config:{}}];
   real.connections={'26':{status:'connected',tx_capable:true,local_node_num:1},'28':{status:'connected'}};
   return json(r,real);
  });
  await page.route('**/api/radios/available',r=>json(r,{success:true,data:[{id:26,name:'PT2VHF-4 - Móvel',kind:'serial',active:true,status:'connected'}]}));
  await page.route('**/api/nodes/sources',r=>json(r,{success:true,data:[{node_num:1,source_id:26,observed:1},{node_num:2,source_id:28,observed:1},{node_num:3,source_id:28,observed:1}]}));
  await page.route('**/api/nodes',r=>json(r,{success:true,data:[1,2,3].map(n=>({node_num:n,node_id:'!0000000'+n,long_name:'Nó '+n,short_name:'N'+n,last_seen_ms:Date.now()}))}));
  await page.route(/\/api\/(packets|messages)(\?.*)?$/,r=>{requests.push(new URL(r.request().url()).pathname+new URL(r.request().url()).search);return json(r,{success:true,data:[]});});
  await page.goto('http://127.0.0.1:8810/mapa');
  await page.waitForFunction(()=>typeof setViewSource==='function'&&state.sources.length===2);
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();});
  await page.click('#radioConnectionStatus');
  await page.waitForFunction(()=>document.querySelector('[data-view-source="28"]'));
  const out={};
  out.menu=await page.evaluate(()=>[...document.querySelectorAll('[data-view-source]')].map(b=>b.innerText.replace(/\s+/g,' ').trim()));
  await page.click('[data-view-source="28"]');
  await page.waitForFunction(()=>nodes.length===2&&$('viewSourceChip')&&!$('viewSourceChip').hidden);
  out.mqtt=await page.evaluate(()=>({nodes:nodes.map(n=>n.node_num),chip:$('viewSourceChip').innerText,map:mapSourceFilter,stats:statsFilters().source,
   stored:localStorage.getItem('mesh.viewSource')}));
  out.requested=requests.some(u=>u==='/api/packets?source=28')&&requests.some(u=>u==='/api/messages?source=28');
  await page.click('#viewSourceChip');
  await page.waitForFunction(()=>nodes.length===3&&$('viewSourceChip').hidden);
  out.all=await page.evaluate(()=>({nodes:nodes.length,map:mapSourceFilter,stats:statsFilters().source,stored:localStorage.getItem('mesh.viewSource')}));
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1));
  assert.deepEqual(out.menu,['Todas as conexões','PT2VHF-4 - Móvel USB','Platorm MQTT']);
  assert.deepEqual(out.mqtt.nodes,[2,3]);assert(out.mqtt.chip.includes('Todas as conexões'));  // v0.6.48: o nome vai na barra (#194)
  assert.equal(out.mqtt.map,'28');assert.equal(out.mqtt.stats,'28');assert.equal(out.mqtt.stored,'28');
  assert(out.requested,'packets/messages filtered on the server');
  assert.deepEqual(out.all,{nodes:3,map:'',stats:'all',stored:null});
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.47 OK',JSON.stringify(out.mqtt));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
