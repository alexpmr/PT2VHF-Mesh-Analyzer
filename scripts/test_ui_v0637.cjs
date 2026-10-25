/* v0.6.37 Chromium regression: active radio selector (#152), detected radio notice (#149), auto add (#151). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8802','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8802/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],calls=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(route,body)=>route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  let notices=[{id:'n1',kind:'serial',address:'COM5',name:'VHF3',verified:true,detected_ms:Date.now()}];
  let autoPolls=0;
  await page.route('**/api/radios/available',r=>json(r,{success:true,data:[
    {id:1,name:'Base USB',kind:'serial',active:true,status:'connected'},
    {id:2,name:'Base Wi-Fi',kind:'tcp',active:false,status:'standby'}],switch:{phase:'idle'}}));
  await page.route('**/api/radios/activate',r=>{calls.push('activate:'+r.request().postData());return json(r,{success:true,data:{state:'switching'}});});
  await page.route('**/api/radios/switch',r=>json(r,{success:true,data:{phase:'done'}}));
  await page.route('**/api/devices/detected',r=>json(r,{success:true,data:notices}));
  await page.route('**/api/devices/accept',r=>{calls.push('accept:'+r.request().postData());
    notices=[{...notices[0],job:{phase:'done',source:{id:3,name:'VHF3 USB'},other_active:true}}];
    return json(r,{success:true,job:{phase:'connecting'}});});
  await page.route('**/api/devices/dismiss',r=>{calls.push('dismiss:'+r.request().postData());return json(r,{success:true});});
  await page.route('**/api/devices/autoadd/start',r=>json(r,{success:true,data:{running:true,phase:'Procurando em USB, Wi-Fi e Bluetooth…',results:[]}}));
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:++autoPolls<2?{running:true,phase:'Verificando 2 dispositivo(s)…',results:[]}:
    {running:false,phase:'done',errors:[],results:[{kind:'serial',address:'COM5',name:'x',outcome:'added',detail:'VHF3 USB'},
      {kind:'tcp',address:'192.168.0.20',name:'y',outcome:'configured',detail:'Já configurado'},
      {kind:'serial',address:'COM9',name:'z',outcome:'no_response',detail:'Timed out'}]}}));
  await page.goto('http://127.0.0.1:8802/mapa');
  await page.waitForFunction(()=>typeof openRadioMenu==='function'&&map!==null);
  const result=await page.evaluate(async()=>{
   const sleep=ms=>new Promise(r=>setTimeout(r,ms)),out={};
   state.sources=[{id:1,name:'Base USB',kind:'serial',enabled:true},{id:2,name:'Base Wi-Fi',kind:'tcp',enabled:true}];
   state.connections={'1':{status:'connected'},'2':{status:'standby'}};
   updateRadioConnectionIndicator();
   // #152 seletor
   $('radioConnectionStatus').click();await sleep(150);
   out.menuOpen=!$('radioMenu').hidden;
   out.items=[...$('radioMenu').querySelectorAll('[data-radio]')].map(b=>b.textContent+(b.disabled?' [off]':''));
   out.focusInMenu=$('radioMenu').contains(document.activeElement);
   document.body.click();out.closedOutside=$('radioMenu').hidden;
   $('radioConnectionStatus').click();await sleep(150);
   $('radioMenu').querySelector('[data-radio="2"]').click();
   // O texto "Trocando para…" só aparece depois da resposta do servidor (lenta no runner do Windows).
   for(let i=0;i<60&&!$('radioConnectionText').textContent.includes('Trocando');i++)await sleep(50);
   out.switching=$('radioConnectionText').textContent;
   out.closedAfterChoice=$('radioMenu').hidden;
   // #149 aviso
   await refreshDeviceNotices();
   out.notice=$('deviceNotices').innerText;
   $('deviceNotices').querySelector('[data-notice-add]').click();await sleep(300);
   out.afterAdd=$('deviceNotices').innerText;
   // #151 adicionar automaticamente
   await setView('settings');showSettings('sources');
   out.buttons=[$('sourceAddManual').textContent,$('sourceAddAuto').textContent,$('scanDevices').textContent];
   $('sourceAddAuto').click();await sleep(2600);
   out.summary=$('autoAddResult').innerText;
   out.autoEnabled=!$('sourceAddAuto').disabled;
   return out;
  });
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(result));
  assert(result.menuOpen&&result.focusInMenu&&result.closedOutside&&result.closedAfterChoice);
  assert.equal(result.items.length,2);assert(result.items[0].includes('Base USB')&&result.items[0].includes('[off]'));
  assert(result.items[1].includes('Base Wi-Fi')&&result.items[1].includes('usar este'));
  assert(calls.includes('activate:{"id":2}'));assert(result.switching.includes('Base Wi-Fi'));
  assert(result.notice.includes('VHF3')&&result.notice.includes('Adicionar e conectar')&&result.notice.includes('Nunca para este dispositivo'));
  assert(calls.includes('accept:{"id":"n1"}'));assert(result.afterAdd.includes('VHF3 USB adicionado')&&result.afterAdd.includes('Usar este agora'));
  assert.deepEqual(result.buttons,['Adicionar conexão manualmente','Adicionar automaticamente','Detectar automaticamente']);
  assert(result.summary.includes('1 adicionada(s)')&&result.summary.includes('1 já configurada(s)')&&result.summary.includes('sem resposta Meshtastic'));
  assert(result.autoEnabled);
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.37 OK',JSON.stringify(result));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
