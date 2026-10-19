/* Real Chromium smoke test, isolated profile and no radio configuration. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8796','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8796/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:950}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  await page.goto('http://127.0.0.1:8796/mapa');
  await page.waitForFunction(()=>typeof renderChat==='function'&&map!==null);
  await page.evaluate(()=>{refreshAll=async()=>{};});
  const result=await page.evaluate(async()=>{
   await setView('messages');
   const ts=Date.now();messages=[{id:1,source_id:1,direction:'rx',channel:0,to_node:4294967295,from_node:42,text:'Linha 1\nLinha 2\n\nFim <script>',timestamp_ms:ts-240000}];
   currentChat='channel:0';renderChat();
   const body=document.querySelector('.bubble>div'),time=document.querySelector('.bubble time');
   const out={text:body.innerText,whiteSpace:getComputedStyle(body).whiteSpace,time:time.innerText,fullTime:time.title};
   out.oldTime=messageTimeHtml(new Date(2020,0,2,12).getTime(),new Date(2026,9,19,12));
   await setView('map');
   nodes=[{node_num:1,long_name:'Match A',latitude:-15,longitude:-47,last_seen_ms:ts},{node_num:2,long_name:'Match B',latitude:-15,longitude:-46,last_seen_ms:ts},{node_num:3,long_name:'Other C',latitude:-15,longitude:-45,last_seen_ms:ts}];
   communications=[{source_id:1,from_node:1,to_node:2,transport:'radio',observations:1,last_seen_ms:ts},{source_id:1,from_node:1,to_node:3,transport:'radio',observations:1,last_seen_ms:ts}];links=[];
   $('showMapNodes').checked=true;$('showMapLinks').checked=true;$('mapIdentifiedOnly').checked=false;$('mapWindow').value='all';$('mapMinObservations').value=1;
   $('mapSearchInput').value='Match';renderMap();out.filteredLinks=linkLayer.getLayers().length;
   $('mapSearchInput').value='nothing';renderMap();out.noLinks=linkLayer.getLayers().length;
   $('mapSearchInput').value='';renderMap();out.allLinks=linkLayer.getLayers().length;
   out.collapsed=!$('mapTaskQueue').open;
   state.sources=[{id:1,name:'Detected Radio',kind:'tcp',enabled:true}];state.connections={'1':{status:'connected'}};
   updateRadioConnectionIndicator();out.connected=$('radioConnectionText').textContent;
   state.connections={'1':{status:'disconnected'}};updateRadioConnectionIndicator();out.disconnected=$('radioConnectionText').textContent;
   await setView('automations');await loadAutomation();
   $('autoRecent').value=25;$('autoRecent').dispatchEvent(new Event('input',{bubbles:true}));
   out.saveEnabled=!$('autoSaveButton').disabled;
   setView('messages');await new Promise(r=>setTimeout(r,20));
   out.leavePrompt=!!document.querySelector('dialog[open]');
   document.querySelector('[data-choice="continue"]').click();await new Promise(r=>setTimeout(r,20));out.stayed=view==='automations';
   setView('messages');await new Promise(r=>setTimeout(r,20));document.querySelector('[data-choice="discard"]').click();await new Promise(r=>setTimeout(r,20));out.discarded=view==='messages'&&!autoDirty;
   return out;
  });
  assert.equal(result.whiteSpace,'pre-wrap');assert(result.text.includes('Linha 1\nLinha 2\n\nFim <script>'));
  assert.equal(result.time,'há 4 minutos');assert(result.fullTime);assert(result.oldTime.includes('2020'));
  assert.equal(result.filteredLinks,1);assert.equal(result.noLinks,0);assert.equal(result.allLinks,2);
  assert(result.collapsed);assert.equal(result.connected,'Detected Radio');assert.equal(result.disconnected,'desconectado');
  assert(result.saveEnabled&&result.leavePrompt&&result.stayed&&result.discarded);
  assert.deepEqual(errors,[]);console.log('Chromium UI regression OK',JSON.stringify(result));
 }finally{if(browser)await browser.close();server.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
