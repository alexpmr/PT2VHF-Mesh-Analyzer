/* v0.6.48 Chromium regression: barra superior mostra a conexão vista (#194) e PIN no "Adicionar automaticamente" (#191). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8811','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8811/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],pins=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('dialog',d=>d.accept('123456'));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(r,body)=>r.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}}));
  await page.route('**/api/state',async r=>{
   const real=await (await r.fetch()).json();
   real.sources=[{id:26,name:'PT2VHF-4 - Móvel',kind:'serial',enabled:true,config:{port:'COM5'}},
                 {id:28,name:'Platorm',kind:'mqtt',enabled:true,config:{}}];
   real.connections={'26':{status:'connected',tx_capable:true,local_node_num:1},'28':{status:'connected'}};
   return json(r,real);
  });
  await page.route('**/api/devices/pair-address',r=>{pins.push(JSON.parse(r.request().postData()));return json(r,{success:true,job:{phase:'pairing'}});});
  await page.goto('http://127.0.0.1:8811/mapa');
  await page.waitForFunction(()=>typeof setViewSource==='function'&&state.sources.length===2);
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();localStorage.removeItem('mesh.viewSource');});
  const out={};
  out.radio=await page.evaluate(()=>$('radioConnectionText').innerText);
  await page.evaluate(()=>setViewSource('28'));
  await page.waitForFunction(()=>$('radioConnectionText').innerText.includes('Platorm'));
  out.mqtt=await page.evaluate(()=>{const chip=$('viewSourceChip'),r=chip.getBoundingClientRect(),p=$('radioConnectionStatus').getBoundingClientRect();
   return {text:$('radioConnectionText').innerText,view:$('radioConnectionStatus').dataset.view,chipVisible:!chip.hidden&&r.width>0&&r.left>=p.right-1&&Math.abs(r.top-p.top)<30};});
  await page.click('#viewSourceChip');
  await page.waitForFunction(()=>!$('radioConnectionText').innerText.includes('Platorm'));
  out.back=await page.evaluate(()=>({text:$('radioConnectionText').innerText,view:$('radioConnectionStatus').dataset.view||null}));
  // Resultado do "Adicionar automaticamente" com rádio BLE sem resposta: botão de PIN.
  await page.evaluate(()=>{setView('settings');showSettings('sources');renderAutoAdd({running:false,errors:[],results:[
    {kind:'ble',address:'44:1B:F6:70:9C:25',name:'Meshtastic_9c25',outcome:'no_response',detail:'Bluetooth: falhou ao abrir a conexão'},
    {kind:'serial',address:'COM5',name:'COM5',outcome:'configured',detail:'Já configurado'}]});});
  out.buttons=await page.evaluate(()=>document.querySelectorAll('[data-autoadd-pin]').length);
  out.hint=await page.evaluate(()=>$('autoAddResult').innerText.includes('123456'));
  await page.click('[data-autoadd-pin]');
  await page.waitForFunction(()=>document.querySelector('[data-autoadd-pin]').disabled);
  if(process.env.MESH_DEBUG)console.log(JSON.stringify({out,pins},null,1));
  assert.equal(out.radio,'PT2VHF-4 - Móvel');
  assert.equal(out.mqtt.text,'Platorm · MQTT (TX: PT2VHF-4 - Móvel)');assert.equal(out.mqtt.view,'other');assert(out.mqtt.chipVisible,'chip next to the pill');
  assert.deepEqual(out.back,{text:'PT2VHF-4 - Móvel',view:null});
  assert.equal(out.buttons,1);assert(out.hint);
  assert.deepEqual(pins,[{address:'44:1B:F6:70:9C:25',pin:'123456',name:'Meshtastic_9c25'}]);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.48 OK',JSON.stringify(out.mqtt));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
