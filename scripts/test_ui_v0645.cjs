/* v0.6.45 Chromium regression (#185): protocolo MeshCore no cadastro de conexões. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8808','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8808/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const idle={success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}};
  await page.route('**/api/devices/autoadd',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(idle)}));
  await page.goto('http://127.0.0.1:8808/configuracoes/conexoes');
  await page.waitForFunction(()=>typeof showSourceFields==='function'&&document.querySelector('#sourceProtocol'));
  const out={};
  out.fields=await page.evaluate(()=>{
   firstRunDialogChecked=true;dismissFirstRunDialog();resetSourceForm();$('sourceFormCard').hidden=false;
   const vis=id=>getComputedStyle($(id).closest('.field')).display!=='none';
   const r={};
   $('sourceKind').value='ble';$('sourceKind').dispatchEvent(new Event('change'));
   r.blePinHidden=!vis('sourceBlePin');
   $('sourceProtocol').value='meshcore';$('sourceProtocol').dispatchEvent(new Event('change'));
   r.blePinShown=vis('sourceBlePin');
   $('sourceKind').value='tcp';$('sourceKind').dispatchEvent(new Event('change'));
   r.tcpPort=$('sourceTcpPort').value;r.protocolVisible=vis('sourceProtocol');
   $('sourceKind').value='mqtt';$('sourceKind').dispatchEvent(new Event('change'));
   r.protocolHiddenMqtt=!vis('sourceProtocol');
   return r;
  });
  // Salva uma conexão MeshCore desativada e confere o cartão e a edição.
  out.saved=await page.evaluate(async()=>{
   resetSourceForm();$('sourceFormCard').hidden=false;
   $('sourceName').value='MeshCore Casa';$('sourceKind').value='tcp';$('sourceKind').dispatchEvent(new Event('change'));
   $('sourceProtocol').value='meshcore';$('sourceProtocol').dispatchEvent(new Event('change'));
   $('sourceHost').value='192.168.1.50';$('sourceEnabled').checked=false;
   $('sourceForm').requestSubmit();
   // Salvar e recarregar o estado leva mais de 4 s no runner do Windows às vezes.
   const saved=()=>(state.sources||[]).find(x=>x.name==='MeshCore Casa');
   for(let i=0;i<300&&!saved();i++)await new Promise(r=>setTimeout(r,100));
   const s=saved();renderSources();
   editSource(s.id);
   return {config:s.config,badge:$('sourceCards').innerText.includes('MeshCore'),editProtocol:$('sourceProtocol').value,editPort:$('sourceTcpPort').value};
  });
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1));
  assert(out.fields.blePinHidden&&out.fields.blePinShown&&out.fields.protocolVisible&&out.fields.protocolHiddenMqtt);
  assert.equal(out.fields.tcpPort,'5000');
  assert.equal(out.saved.config.protocol,'meshcore');assert.equal(out.saved.config.port,5000);
  assert(out.saved.badge);assert.equal(out.saved.editProtocol,'meshcore');assert.equal(out.saved.editPort,'5000');
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.45 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
