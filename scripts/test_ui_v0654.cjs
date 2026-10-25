/* v0.6.54 Chromium regression: cor da barra do rádio por tipo de conexão (USB, Bluetooth, Wi-Fi, MQTT). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8813','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8813/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  await page.route('**/api/devices/autoadd',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}})}));
  await page.goto('http://127.0.0.1:8813/mapa');
  await page.waitForFunction(()=>typeof updateRadioConnectionIndicator==='function'&&typeof setViewSource==='function');
  const out=await page.evaluate(()=>{
   firstRunDialogChecked=true;dismissFirstRunDialog();
   const r={};
   for(const kind of ['serial','ble','tcp']){
    state={...state,sources:[{id:1,name:'Rádio '+kind,kind,enabled:true,config:{}},{id:2,name:'Platorm',kind:'mqtt',enabled:true,config:{}}],
           connections:{'1':{status:'connected'},'2':{status:'connected'}}};
    viewSource='';updateRadioConnectionIndicator();
    const pill=$('radioConnectionStatus'),dot=pill.querySelector('.radioDot');
    r[kind]={kind:pill.dataset.kind,border:getComputedStyle(pill).borderTopColor,dot:getComputedStyle(dot).backgroundColor};
   }
   viewSource='2';updateRadioConnectionIndicator();
   const pill=$('radioConnectionStatus');r.mqtt={kind:pill.dataset.kind,border:getComputedStyle(pill).borderTopColor};
   viewSource='';
   return r;
  });
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1));
  assert.equal(out.serial.border,'rgb(35, 141, 88)');
  assert.equal(out.ble.border,'rgb(59, 130, 246)');assert.equal(out.ble.dot,'rgb(96, 165, 250)');
  assert.equal(out.tcp.border,'rgb(224, 138, 46)');assert.equal(out.tcp.dot,'rgb(245, 158, 11)');
  assert.equal(out.mqtt.kind,'mqtt');assert.equal(out.mqtt.border,'rgb(160, 108, 255)');
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.54 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
