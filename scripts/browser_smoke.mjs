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
  for (let i = 0; i < 100 && !existsSync(portFile); i++) await delay(200);
  const port = readFileSync(portFile, 'utf8').split('\n')[0].trim();
  const target = await fetch(`http://127.0.0.1:${port}/json/new?http://127.0.0.1:5173`, {method: 'PUT'}).then(r => r.json());
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
  await send('Page.navigate', {url: 'http://127.0.0.1:5173/'});
  await send('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false});
  await until(`Boolean([...document.querySelectorAll('button')].find(b => b.textContent.includes('Load sample student')))`);
  await evaluate(`[...document.querySelectorAll('button')].find(b => b.textContent.includes('Load sample student')).click()`);
  await until(`document.querySelector('input[maxlength="150"]').value === 'Demo Student'`);
  await evaluate(`[...document.querySelectorAll('label.checkbox')].find(label => label.textContent.includes('I have reviewed')).querySelector('input').click()`);
  await evaluate(`[...document.querySelectorAll('button')].find(b => b.textContent.includes('Screen student')).click()`);
  await until(`document.querySelector('.result-badge')?.textContent === 'Eligible'`);
  const directory = resolve('artifacts'); mkdirSync(directory, {recursive: true});
  await evaluate('window.scrollTo(0, 0)');
  await delay(500);
  let screenshot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  writeFileSync(join(directory, 'desktop-screening.png'), Buffer.from(screenshot.data, 'base64'));
  await send('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  await delay(500);
  const overflow = await evaluate('document.documentElement.scrollWidth > window.innerWidth');
  if (overflow) throw new Error('Mobile layout overflows horizontally.');
  screenshot = await send('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  writeFileSync(join(directory, 'mobile-screening.png'), Buffer.from(screenshot.data, 'base64'));
  console.log('Browser smoke passed: sample entry, confirmation, live eligible result, desktop and mobile layouts without horizontal overflow.');
  await send('Browser.close');
} finally {
  socket?.close();
  edge.kill();
}
