/* v0.6.41 Chromium regression: análise de enlace entre 2 pontos (#179) e melhor ponto em polígono (#180).
   O servidor real é usado; só a consulta de elevação ao Open-Meteo é trocada por um terreno sintético. */
const {chromium}=require('playwright');
const {spawn}=require('child_process');
const fs=require('fs');
const assert=require('assert/strict');
const os=require('os');
const path=require('path');
const FAKE=`
import math,runpy,sys
import mesh_analyzer.survey as s
def hills(points):
    out=[]
    for la,lo in points:
        out.append(800+300*math.exp(-((la+15.80)**2+(lo+47.90)**2)/0.01**2)+150*math.exp(-((la+15.77)**2+(lo+47.87)**2)/0.006**2)
                   +40*math.exp(-((la+15.83)**2+(lo+47.93)**2)/0.004**2))
    return out
s.default_fetcher=lambda cache_dir=None: hills
sys.argv=['launch.py']+sys.argv[1:]
runpy.run_path('launch.py',run_name='__main__')
`;
(async()=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'mesh-ui-'));
 const server=spawn(process.env.PYTHON||'python',['-c',FAKE,'--headless','--no-browser','--port','8806','--data-dir',dir],{stdio:'ignore'});
 let browser;
 try{
  let ready=false;
  for(let i=0;i<100;i++){try{ready=(await fetch('http://127.0.0.1:8806/health')).ok;}catch{} if(ready)break;await new Promise(r=>setTimeout(r,100));}
  assert(ready,'HTTP service did not start');
  const options={headless:true,args:['--no-sandbox']};
  if(process.env.MESH_CHROMIUM_EXE)options.executablePath=process.env.MESH_CHROMIUM_EXE;
  else if(process.platform==='win32')options.channel='chrome';
  browser=await chromium.launch(options);
  const page=await browser.newPage({viewport:{width:1400,height:900}}),errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  if(process.env.MESH_LEAFLET_PATH)await page.route('**/leaflet.js',r=>r.fulfill({contentType:'text/javascript',body:fs.readFileSync(process.env.MESH_LEAFLET_PATH,'utf8')}));
  await page.route(/tile|arcgisonline/,r=>r.fulfill({status:204,body:''}));
  // Num computador real (CI no Windows) a busca de primeira abertura e os avisos de rádio detectado
  // podem aparecer por cima do mapa durante os cliques; aqui eles não fazem parte do teste.
  const idle={success:true,data:{first_run:false,running:false,phase:'done',results:[],added:[]}};
  await page.route('**/api/devices/autoadd',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(idle)}));
  await page.route('**/api/devices/autoadd/start',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(idle)}));
  await page.route('**/api/devices/detected',r=>r.fulfill({contentType:'application/json',body:JSON.stringify({success:true,data:[]})}));
  await page.goto('http://127.0.0.1:8806/mapa');
  await page.waitForFunction(()=>typeof openLinkTool==='function'&&map!==null);
  await page.evaluate(()=>{firstRunDialogChecked=true;dismissFirstRunDialog();$('firstRunSearch').hidden=true;map.setView([-15.80,-47.90],12,{animate:false});});
  const box=await page.locator('#map').boundingBox();
  const px=async(lat,lon)=>{const p=await page.evaluate(([a,b])=>{const q=map.latLngToContainerPoint([a,b]);return [q.x,q.y];},[lat,lon]);return [box.x+p[0],box.y+p[1]];};
  const out={};
  // #179: menu Ver → enlace; dois cliques no mapa; perfil, veredito e PDF.
  await page.click('#mapVisibilityBtn');await page.click('#mapToolLink');
  await page.waitForSelector('#linkHint');
  let [x,y]=await px(-15.80,-47.96);await page.mouse.click(x,y);
  [x,y]=await px(-15.80,-47.84);await page.mouse.click(x,y);
  await page.waitForSelector('#linkResult .verdictBadge',{timeout:15000});
  out.link=await page.evaluate(async()=>{
   const r=mapTool.result;
   const pdf=await fetch('/api/survey/pdf',{method:'POST',headers:{'Content-Type':'application/json','X-PT2VHF-CSRF':csrf},body:JSON.stringify({kind:'link',...linkPayload()})});
   return {verdict:r.verdict,blockedBy:r.worst&&Math.abs(r.worst.lon+47.90)<0.01,svg:!!document.querySelector('#linkResult svg.profileSvg'),
     km:Math.round(r.distance_m/1000),diff:r.budget.diffraction_db,line:!!mapTool.line,worst:!!mapTool.worstMarker,hint:$('linkHint').textContent,
     pdf:pdf.headers.get('Content-Type'),pdfSize:(await pdf.arrayBuffer()).byteLength,pdfBtn:!$('linkPdf').disabled};
  });
  // Antenas mais altas mudam o resultado.
  await page.evaluate(()=>{document.querySelector('#mapToolBody .toolParams').open=true;});
  await page.fill('[data-link-param="height_a"]','120');await page.dispatchEvent('[data-link-param="height_a"]','change');
  await page.fill('[data-link-param="height_b"]','120');await page.dispatchEvent('[data-link-param="height_b"]','change');
  await page.waitForFunction(()=>mapTool.result&&mapTool.result.params.height_b===120,null,{timeout:15000});
  out.raised=await page.evaluate(()=>({margin:mapTool.result.budget.margin_db,diff:mapTool.result.budget.diffraction_db}));
  await page.evaluate(()=>document.activeElement.blur());await page.keyboard.press('Escape');
  out.closed=await page.evaluate(()=>mapTool===null&&$('mapToolPanel').hidden&&toolLayer.getLayers().length===0);
  // #180: polígono clicado no mapa, Ctrl+Z, fechar no primeiro vértice.
  await page.click('#mapVisibilityBtn');await page.click('#mapToolSurvey');
  await page.waitForSelector('#surveyHint');
  const corners=[[-15.75,-47.95],[-15.75,-47.85],[-15.85,-47.85],[-15.85,-47.95]];
  for(const c of corners){[x,y]=await px(...c);await page.mouse.click(x,y);}
  [x,y]=await px(-15.86,-47.90);await page.mouse.click(x,y);
  out.beforeUndo=await page.evaluate(()=>mapTool.vertices.length);
  await page.keyboard.press('Control+z');
  out.afterUndo=await page.evaluate(()=>mapTool.vertices.length);
  [x,y]=await px(...corners[0]);await page.mouse.click(x,y);
  await page.waitForSelector('tr[data-survey-rank]',{timeout:20000});
  out.survey=await page.evaluate(()=>{
   const r=mapTool.result,rows=[...document.querySelectorAll('tr[data-survey-rank]')];
   return {closed:mapTool.closed,ranks:rows.map(r=>Number(r.dataset.surveyRank)),elev:r.points.map(p=>p.elevation_m),
     markers:mapTool.pointMarkers.length,area:r.area_km2,first:[r.points[0].lat,r.points[0].lon],csv:!$('surveyCsv').disabled,pdf:!$('surveyPdf').disabled,
     panelText:$('mapToolBody').textContent.includes('Área:')};
  });
  // Clique na linha da tabela destaca o marcador; enlace do ponto 2 até a referência entra no PDF.
  await page.click('tr[data-survey-rank="2"] td:first-child');
  out.highlight=await page.evaluate(()=>!!mapTool.pointMarkers[1].getElement()?.classList.contains('active'));
  await page.click('[data-survey-link="2"]');await page.click('[data-survey-link-row="2"] [data-sl-run]');
  await page.waitForSelector('[data-survey-link-row="2"] .verdictBadge',{timeout:15000});
  out.surveyPdf=await page.evaluate(async()=>{
   const res=await fetch('/api/survey/pdf',{method:'POST',headers:{'Content-Type':'application/json','X-PT2VHF-CSRF':csrf},body:JSON.stringify(surveyPdfPayload())});
   return {type:res.headers.get('Content-Type'),size:(await res.arrayBuffer()).byteLength,links:surveyPdfPayload().links.length};
  });
  // Edição: remover vértice com o botão direito refaz a busca.
  await page.evaluate(()=>{mapTool.vertexMarkers[0].fire('contextmenu',{originalEvent:new MouseEvent('contextmenu')});});
  out.removed=await page.evaluate(()=>mapTool.vertices.length);
  await page.evaluate(()=>{mapTool.vertexMarkers[0].fire('contextmenu',{originalEvent:new MouseEvent('contextmenu')});});
  out.minVertices=await page.evaluate(()=>mapTool.vertices.length);
  // Salvar e reabrir.
  await page.evaluate(()=>{document.querySelector('#mapToolBody details.toolParams').open=true;});
  await page.fill('#surveyName','Serra teste');await page.click('#surveySave');
  await page.waitForFunction(()=>surveyDefaults.saved.length===1);
  await page.keyboard.press('Escape');
  await page.evaluate(()=>openSurveyTool(surveyDefaults.saved[0]));
  await page.waitForFunction(()=>mapTool?.result?.points?.length>0,null,{timeout:15000});
  out.reopened=await page.evaluate(()=>({name:mapTool.name,vertices:mapTool.vertices.length,closed:mapTool.closed}));
  if(process.env.MESH_DEBUG)console.log(JSON.stringify(out,null,1));
  assert.equal(out.link.verdict!=='viable',true);assert(out.link.blockedBy&&out.link.svg&&out.link.line&&out.link.worst&&out.link.pdfBtn);
  assert.equal(out.link.km,13);assert.equal(out.link.pdf,'application/pdf');assert(out.link.pdfSize>3000);
  assert(out.raised.diff<out.link.diff);
  assert(out.closed);
  assert.equal(out.beforeUndo,5);assert.equal(out.afterUndo,4);
  assert(out.survey.closed&&out.survey.panelText&&out.survey.csv&&out.survey.pdf);
  assert.deepEqual(out.survey.ranks,out.survey.ranks.slice().sort((a,b)=>a-b));
  assert.deepEqual(out.survey.elev,out.survey.elev.slice().sort((a,b)=>b-a));
  assert(out.survey.elev.length>=3&&out.survey.markers===out.survey.elev.length);
  assert(Math.abs(out.survey.first[0]+15.80)<0.01&&Math.abs(out.survey.first[1]+47.90)<0.01);
  assert(out.highlight);
  assert.equal(out.surveyPdf.type,'application/pdf');assert(out.surveyPdf.size>5000);assert.equal(out.surveyPdf.links,1);
  assert.equal(out.removed,3);assert.equal(out.minVertices,3);
  assert.deepEqual(out.reopened,{name:'Serra teste',vertices:3,closed:true});
  assert.deepEqual(errors,[]);console.log('Chromium UI v0.6.41 OK',JSON.stringify(out));
 }finally{
  if(browser)await browser.close();
  server.kill();
 }
})().catch(e=>{console.error(e);process.exit(1);});
