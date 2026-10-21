/* v0.6.36 Chromium regression: message times (#144), chat scroll (#145), update label (#146). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8799','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8799/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:700}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  await page.goto('http://127.0.0.1:8799/mapa');
  await page.waitForFunction(()=>typeof renderChat==='function'&&map!==null);
  const result=await page.evaluate(async()=>{
   refreshAll=async()=>{};
   await setView('messages');
   const out={},base=new Date(2026,9,21,15,0,0).getTime();
   // #144: distinct ages from one fixed clock; future and invalid are not invented ages.
   const now=new Date(base);
   out.ages=[0,1,3,4,15,90].map(m=>messageTimeLabel(base-m*60000,now).label);
   out.yesterday=messageTimeLabel(base-86400000,now).label;
   out.future=messageTimeLabel(base+30*60000,now);
   out.invalid=messageTimeLabel(0,now);
   // #145: long conversation, user scrolls up, periodic refresh keeps position.
   const ts=Date.now();
   messages=Array.from({length:120},(_,i)=>({id:i+1,source_id:1,direction:i%3?'rx':'tx',channel:0,to_node:4294967295,from_node:42,
     text:'Mensagem '+i+(i%5?'':'\nsegunda linha'),timestamp_ms:ts-(120-i)*60000,state:'received'}));
   currentChat='channel:0';renderChat();
   const box=$('bubbles');
   out.startsAtBottom=box.scrollHeight-box.scrollTop-box.clientHeight<=48;
   box.scrollTop=200;box.dispatchEvent(new Event('scroll'));
   const before=box.scrollTop,firstTime=box.querySelector('time').textContent;
   for(let i=0;i<5;i++)renderChat();
   out.keptOnRefresh=box.scrollTop===before;
   messages=[...messages,{id:999,source_id:1,direction:'rx',channel:0,to_node:4294967295,from_node:42,text:'nova',timestamp_ms:Date.now(),state:'received'}];
   renderChat();
   out.keptOnNew=Math.abs(box.scrollTop-before)<=1;
   out.newButton=!$('bubblesNewMessages').hidden;
   $('bubblesNewMessages').click();
   out.jumped=box.scrollHeight-box.scrollTop-box.clientHeight<=48&&$('bubblesNewMessages').hidden;
   messages=[...messages,{id:1000,source_id:1,direction:'rx',channel:0,to_node:4294967295,from_node:42,text:'segue no final',timestamp_ms:Date.now(),state:'received'}];
   renderChat();
   out.followsAtBottom=box.scrollHeight-box.scrollTop-box.clientHeight<=48;
   out.timeStillShown=!!firstTime;
   // #146: label without version number.
   updateVersionState({current:'0.6.36',latest:'0.6.36',available:false,checked_at:Date.now()/1000,interval_minutes:15});
   out.latest=[$('topUpdate').textContent,getComputedStyle($('topUpdate')).color];
   updatePromptedFor='9.9.9';
   updateVersionState({current:'0.6.36',latest:'9.9.9',available:true,checked_at:Date.now()/1000,interval_minutes:15});
   out.available=[$('topUpdate').textContent,$('topUpdate').title];
   updateVersionState({current:'0.6.36',checked_at:null});
   out.waiting=$('topUpdate').textContent;
   updateVersionState({current:'0.6.36',error:'offline',checked_at:Date.now()/1000});
   out.error=$('topUpdate').textContent;
   return out;
  });
  assert.deepEqual(result.ages,['agora','há 1 minuto','há 3 minutos','há 4 minutos','há 15 minutos','há 1 hora']);
  assert(result.yesterday.includes('20/10/2026'));
  assert(result.future.label.includes('21/10/2026')&&result.future.title.includes('à frente'));
  assert.equal(result.invalid,null);
  assert(result.startsAtBottom&&result.keptOnRefresh&&result.keptOnNew&&result.newButton&&result.jumped&&result.followsAtBottom);
  assert.equal(result.latest[0],'Atualizado');assert.equal(result.latest[1],'rgb(161, 231, 191)');
  assert.equal(result.available[0],'Nova Versão');assert(result.available[1].includes('9.9.9'));
  assert(!/\d+\.\d+\.\d+/.test(result.waiting+result.error));
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.36 OK',JSON.stringify(result));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
