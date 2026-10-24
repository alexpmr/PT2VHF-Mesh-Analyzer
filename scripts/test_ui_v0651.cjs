/* v0.6.51 Chromium regression (#198): aba Diagnóstico e atalho no "Adicionar automaticamente". */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8812','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8812/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900},acceptDownloads:true}),errors=[],posts=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(r,body)=>r.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}}));
  await page.route('**/api/diagnostics/verbose',r=>{posts.push('verbose:'+r.request().postData());return json(r,{success:true,verbose:true,seconds_left:600,lines:3});});
  await page.goto('http://127.0.0.1:8812/configuracoes/diagnostico');
  await page.waitForFunction(()=>typeof downloadDiagnostic==='function'&&$('settingsDiagnostics').classList.contains('active'));
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();});
  const out={};
  out.tabLast=await page.evaluate(()=>[...document.querySelectorAll('.settingsTab')].at(-1).dataset.panel);
  await page.check('#diagVerbose');
  await page.waitForFunction(()=>$('diagStatus').textContent.includes('10 minutos'));
  // Diagnóstico real gerado pelo servidor (sem mock), baixado pelo navegador.
  const [download]=await Promise.all([page.waitForEvent('download'),page.click('#diagBuild')]);
  const file=await download.path();
  out.zip=fs.readFileSync(file).subarray(0,2).toString('latin1');
  out.name=download.suggestedFilename();
  await page.waitForFunction(()=>$('diagStatus').textContent.includes('Diagnóstico PT2VHF-Diagnostico-'));
  // Atalho no resultado do "Adicionar automaticamente" quando o Bluetooth falha.
  await page.evaluate(()=>{showSettings('sources');renderAutoAdd({running:false,errors:[],results:[
   {kind:'ble',address:'44:1B:F6:70:8A:69',name:'VHF4_8a68',outcome:'no_response',detail:'Unreachable'}]});});
  out.shortcut=await page.evaluate(()=>!!$('autoAddDiag'));
  if(process.env.MESH_DEBUG)console.log(JSON.stringify({out,posts},null,1));
  assert.equal(out.tabLast,'diagnostics');
  assert.deepEqual(posts,['verbose:{"minutes":10}']);
  assert.equal(out.zip,'PK');assert.match(out.name,/^PT2VHF-Diagnostico-\d{8}-\d{6}\.zip$/);
  assert(out.shortcut);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.51 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
