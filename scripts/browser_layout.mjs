// Uses the locally installed Edge browser and Node's built-in WebSocket API.
// Creates a temporary browser profile; never touches the user's normal profile.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const profile = mkdtempSync(join(tmpdir(), 'mapoly-browser-'));
const edge = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let socket;
let id = 0;
const pending = new Map();
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const key = ++id;
    const timeout = setTimeout(() => { pending.delete(key); reject(new Error(`Timed out: ${method}`)); }, 15000);
    pending.set(key, {resolve: value => {clearTimeout(timeout); resolve(value);}, reject: error => {clearTimeout(timeout); reject(error);}});
    socket.send(JSON.stringify({id: key, method, params}));
  });
}
async function evaluate(expression) {
  const response = await send('Runtime.evaluate', {expression, returnByValue: true, awaitPromise: true});
  if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
  return response.result?.value;
}
async function until(expression) {
  for (let i = 0; i < 60; i++) { if (await evaluate(expression)) return; await delay(250); }
  console.error(await evaluate('JSON.stringify({url:location.href,title:document.title,body:document.body.innerText.slice(0,3000)})'));
  throw new Error(`Browser condition did not become true: ${expression}`);
}

try {
  const portFile = join(profile, 'DevToolsActivePort');
  let port;
  for (let attempt = 0; attempt < 100 && !port; attempt++) {
    try { const value = readFileSync(portFile, 'utf8').split('\n')[0].trim(); if (/^\d+$/.test(value)) port = value; } catch {}
    if (!port) await delay(200);
  }
  if (!port) throw new Error('Browser debugging port did not become available.');
  const target = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method: 'PUT'}).then(r => r.json());
  socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.onopen = resolve; socket.onerror = reject;});
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.method === 'Runtime.exceptionThrown') console.error('Browser exception:', JSON.stringify(message.params));
    if (pending.has(message.id)) {
      const request = pending.get(message.id); pending.delete(message.id);
      message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    }
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setFocusEmulationEnabled', {enabled: true});
  const html = readFileSync('frontend/dist/index.html', 'utf8');
  const jsPath = html.match(/src="([^"]+\.js)"/)[1];
  const cssPath = html.match(/href="([^"]+\.css)"/)[1];
  const css = readFileSync('frontend/dist' + cssPath, 'utf8').replace(/@import\s*(?:url\([^)]*\)|"[^"]*"|'[^']*')\s*;/g, '');
  const js = readFileSync('frontend/dist' + jsPath, 'utf8');
  await send('Page.setDocumentContent', {frameId: (await send('Page.getFrameTree')).frameTree.frame.id, html: '<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>' + css + '</style></head><body><div id="root"></div></body></html>'});
  await evaluate(`window.fetch = async url => ({ok:true,json:async()=>{
    const subjects=['English Language','Mathematics','Physics','Chemistry','Biology','Economics'];
    if(url.includes('session'))return {user:null};
    if(url.includes('catalogue'))return {subjects,grades:['A1','B2','B3','C4','C5','C6','D7','E8','F9'],examinations:[{board:'WAEC',exam_type:'School',label:'WAEC - WASSCE / SSCE (School)'}]};
    if(url.includes('rules'))return {rules:[{id:1,programme:'Computer Science',academic_session:'2026/2027',minimum_jamb:180,minimum_credits:5,max_sittings:2,allow_combining:true,active:true,revision:1,required_subjects:subjects.slice(0,3).map(subject=>({subject,minimum_grade:'C6'}))}]};
    return {available:true};
  }});`);
  if (process.argv[2]) {
    const fixture = JSON.parse(readFileSync(process.argv[2], 'utf8'));
    await evaluate(`{
      const fixture=${JSON.stringify(fixture)}, previous=window.fetch;
      window.fetch=async url=>url.includes('rules') ? {ok:true,json:async()=>fixture.rules} : url.includes('catalogue') ? {ok:true,json:async()=>fixture.catalogue} : url.includes('session') && fixture.user ? {ok:true,json:async()=>({user:fixture.user})} : previous(url);
    }`);
  }
  await evaluate(js);
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false});
  await until(`Boolean([...document.querySelectorAll('button')].find(b => b.textContent.includes('Load sample student')))`);
  await evaluate(`[...document.querySelectorAll('button')].find(b => b.textContent.includes('Load sample student')).click()`);
  await until(`document.querySelector('input[maxlength="150"]').value === 'Demo Student'`);
  const logo = 'data:image/png;base64,' + readFileSync('frontend/public/mapoly-logo.png').toString('base64');
  await evaluate('document.querySelectorAll(".brand-logo,.mobile-brand img").forEach(img => img.src = ' + JSON.stringify(logo) + ')');
  if (await evaluate('/prototype/i.test(document.body.innerText)')) throw new Error('Prototype text is still visible.');
  const sizes = await evaluate('JSON.stringify({body:getComputedStyle(document.body).fontSize,label:getComputedStyle(document.querySelector(".field>span")).fontSize,input:getComputedStyle(document.querySelector("input[type=number]")).fontSize})');
  console.log('Rendered text sizes:', sizes);
  if (await evaluate('getComputedStyle(document.querySelector(".sidebar")).position !== "fixed"')) throw new Error('Workspace stylesheet did not load.');
  const directory = resolve('artifacts'); mkdirSync(directory, {recursive: true});
  await evaluate('window.scrollTo(0, 0)');
  await delay(500);
  let screenshot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  writeFileSync(join(directory, 'desktop-redesign.png'), Buffer.from(screenshot.data, 'base64'));
  const expandedWidth = await evaluate('document.querySelector("main").getBoundingClientRect().width');
  await evaluate('document.querySelector(".sidebar-toggle").click()');
  await until('document.querySelector(".sidebar-toggle").getAttribute("aria-expanded") === "false"');
  if (await evaluate('document.querySelector("main").getBoundingClientRect().width') <= expandedWidth) throw new Error('Collapse did not expand content.');
  await evaluate('document.querySelector(".nav-item").focus()');
  if (await evaluate('getComputedStyle(document.querySelector(".nav-tooltip")).display') === 'none') {
    // Check the focused navigation item's own tooltip (the toggle has one too).
    if (await evaluate('getComputedStyle(document.querySelector(".nav-item .nav-tooltip")).display') === 'none') throw new Error('Keyboard tooltip missing.');
  }
  screenshot = await send('Page.captureScreenshot', {format:'png'});
  writeFileSync(join(directory,'desktop-collapsed.png'),Buffer.from(screenshot.data,'base64'));
  await evaluate('document.querySelector(".sidebar-toggle").click()');
  for (const width of [1024, 820, 768, 390, 320]) {
    await send('Emulation.setDeviceMetricsOverride', {width, height: 900, deviceScaleFactor: 1, mobile: width <= 768});
    await delay(200);
    if (await evaluate('document.documentElement.scrollWidth > window.innerWidth')) throw new Error(`Horizontal overflow at ${width}px`);
    if (width <= 768) {
      if (!await evaluate('getComputedStyle(document.querySelector(".sidebar")).position === "fixed" && Math.abs(document.querySelector(".sidebar").getBoundingClientRect().bottom - innerHeight) < 2')) throw new Error('Mobile navigation is not fixed at bottom.');
      if (!await evaluate('[...document.querySelectorAll(".nav-label")].every(el=>getComputedStyle(el).display!=="none")')) throw new Error('Mobile labels hidden.');
      await evaluate('window.scrollTo(0,document.documentElement.scrollHeight)');
      await delay(150);
      if (!await evaluate('document.querySelector("footer").getBoundingClientRect().bottom <= document.querySelector(".sidebar").getBoundingClientRect().top')) throw new Error('Bottom bar covers footer.');
    }
    await evaluate('window.scrollTo(0,0)');
    screenshot = await send('Page.captureScreenshot', {format:'png'});
    writeFileSync(join(directory,`workspace-${width}.png`),Buffer.from(screenshot.data,'base64'));
  }
  console.log('Layout checks passed: expanded/collapsed desktop, keyboard tooltip, tablet at 1024/820px, bottom navigation at 768/390/320px, no overflow or covered footer. Mocked API; no application servers started.');
  if (process.argv[2]) {
    await evaluate('document.querySelector("button[aria-label=\\"Admission rules\\"]").click()');
    await until('document.querySelectorAll(".rule-grid > section").length === 28');
    await evaluate('document.querySelectorAll(".rule-grid > section:first-child details").forEach(el=>el.open=true)');
    for (const width of [1440, 820, 390, 320]) {
      await send('Emulation.setDeviceMetricsOverride', {width,height:900,deviceScaleFactor:1,mobile:width<=768});
      await delay(150);
      if (await evaluate('document.documentElement.scrollWidth > window.innerWidth')) throw new Error(`Compendium rules overflow at ${width}px`);
      await evaluate('window.scrollTo(0,0)');
      const capture = await send('Page.captureScreenshot', {format:'png'});
      writeFileSync(join(directory,`compendium-${width}.png`),Buffer.from(capture.data,'base64'));
    }
    console.log('All 28 compendium cards and expanded requirements passed desktop, tablet and phone overflow checks.');
    if (await evaluate('Boolean([...document.querySelectorAll("button")].find(b=>b.textContent.includes("Edit rules")))')) {
      await evaluate('[...document.querySelectorAll("button")].find(b=>b.textContent.includes("Edit rules")).click()');
      await until('Boolean(document.querySelector(".criteria-form"))');
      for (const width of [1440, 820, 390, 320]) {
        await send('Emulation.setDeviceMetricsOverride', {width,height:900,deviceScaleFactor:1,mobile:width<=768});
        await evaluate('document.querySelector(".criteria-form").scrollIntoView()');
        await delay(150);
        if (await evaluate('document.documentElement.scrollWidth > window.innerWidth')) throw new Error(`Criteria editor overflow at ${width}px`);
        const capture=await send('Page.captureScreenshot',{format:'png'});
        writeFileSync(join(directory,`criteria-editor-${width}.png`),Buffer.from(capture.data,'base64'));
      }
      console.log('Form-based criteria editor passed desktop, tablet and phone overflow checks.');
    }
  }
  await send('Browser.close');
} finally {
  socket?.close();
  edge.kill();
}
