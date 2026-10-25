/* v0.6.55 Chromium regression (#206): apelido pessoal do nó (menu de contexto, coluna, título). */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['launch.py','--headless','--no-browser','--port','8814','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<80;i++){try{ready=(await fetch('http://127.0.0.1:8814/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[],posts=[];
  page.on('pageerror',e=>errors.push(String(e)));
  const prompts=[];page.on('dialog',d=>{prompts.push(d.message());d.accept('Repetidor da Serra');});
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  const json=(r,body)=>r.fulfill({contentType:'application/json',body:JSON.stringify(body)});
  await page.route('**/api/devices/autoadd',r=>json(r,{success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}}));
  let nick='';
  await page.route('**/api/nodes',r=>json(r,{success:true,data:[{node_num:0x441bf670,node_id:'!441bf670',long_name:'VHF4_8a68',short_name:'V4',friendly_name:nick,last_seen_ms:Date.now()}]}));
  await page.route('**/api/nodes/friendly',r=>{const b=JSON.parse(r.request().postData());posts.push(b);nick=b.friendly_name;
   return json(r,{success:true,node:{node_num:b.node_num,friendly_name:nick}});});
  await page.goto('http://127.0.0.1:8814/nos');
  await page.waitForFunction(()=>typeof editNickname==='function'&&nodes.length===1);
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();openNodeContext(0x441bf670,200,200);});
  const out={};
  out.menu=await page.evaluate(()=>[...document.querySelectorAll('#nodeContextMenu [data-node-action]')].map(b=>b.textContent));
  await page.click('[data-node-action="nickname"]');
  await page.waitForFunction(()=>$('nodesRows').innerText.includes('Repetidor da Serra'));
  out.header=await page.evaluate(()=>$('nodesHeader').innerText);
  out.row=await page.evaluate(()=>$('nodesRows').innerText);
  out.title=await page.evaluate(()=>{showNode(nodes[0]);const t=$('nodeDetailTitle').textContent;closeNodeDetails();return t;});
  out.button=await page.evaluate(()=>$('nodeRename').textContent);
  if(process.env.MESH_DEBUG)console.log(JSON.stringify({out,posts,prompts},null,1));
  assert(out.menu.includes('Dar apelido'));
  assert.deepEqual(posts,[{node_num:0x441bf670,friendly_name:'Repetidor da Serra'}]);
  assert(prompts[0].includes('não muda o nome do rádio'));
  assert(out.header.includes('Apelido'));assert(out.row.includes('Repetidor da Serra')&&out.row.includes('VHF4_8a68'));
  assert.equal(out.title,'Repetidor da Serra (VHF4_8a68) · !441bf670');
  assert.equal(out.button,'Apelido…');
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.55 OK',JSON.stringify(out.menu));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
