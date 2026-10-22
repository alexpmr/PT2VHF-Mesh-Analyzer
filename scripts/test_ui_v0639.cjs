/* v0.6.39 Chromium regression (#162): busca antes do diálogo "Configure sua primeira conexão". */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8804','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8804/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],calls=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(route,body)=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  let search={first_run:true,running:true,phase:'Verificando 1 porta(s) USB…',results:[],added:[]};
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:search}));
  await page.route('**/api/devices/autoadd/start',r=>{calls.push('start:'+r.request().postData());return json(r,{success:true,data:search});});
  await page.route('**/api/devices/autoadd/cancel',r=>{calls.push('cancel');return json(r,{success:true,data:search});});
  await page.goto('http://127.0.0.1:8804/mapa');
  await page.waitForFunction(()=>typeof showFirstRunDialogOnce==='function'&&map!==null&&updateNoticeChecked);
  const step=()=>page.evaluate(async()=>{await showFirstRunDialogOnce();return {search:!$('firstRunSearch').hidden,phase:$('firstRunSearchPhase').textContent,
    dialog:$('firstRunDialog').classList.contains('open'),result:$('firstRunSearchResult').hidden?'':$('firstRunSearchResult').textContent};});
  await page.evaluate(()=>{refreshAll=async()=>{};state.sources=[];firstRunDialogChecked=false;forgetFirstRunShown();dismissFirstRunDialog();});
  const out={};
  out.running=await step();                      // busca em andamento: cartão, sem diálogo
  await page.click('#firstRunSearchCancel');
  search={first_run:true,running:false,phase:'done',results:[{kind:'serial',address:'COM3',outcome:'no_response'}],added:[]};
  out.nothing=await step();                      // nada encontrado: diálogo com resultado
  await page.click('#firstRunSearchAgain');
  await page.waitForFunction(()=>!$('firstRunSearch').hidden,null,{timeout:3000}).catch(()=>{});
  out.again=await page.evaluate(()=>({search:!$('firstRunSearch').hidden,dialog:$('firstRunDialog').classList.contains('open')}));
  search={first_run:true,running:false,phase:'done',results:[{kind:'serial',address:'COM3',outcome:'added'}],added:[{id:1,name:'VHF3 USB',kind:'serial'}]};
  out.added=await step();                        // rádio conectado: nenhum diálogo
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1),calls);
  assert(out.running.search&&!out.running.dialog&&out.running.phase.includes('USB'));
  assert(calls.includes('cancel'));
  assert(!out.nothing.search&&out.nothing.dialog&&out.nothing.result.includes('COM3')&&out.nothing.result.includes('sem resposta'));
  assert(calls.includes('start:{"first_run":true}')&&out.again.search&&!out.again.dialog);
  assert(!out.added.search&&!out.added.dialog);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.39 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
