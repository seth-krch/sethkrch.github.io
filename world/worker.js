// Runs the simulation's real Python in Pyodide, off the page's main thread so the
// page stays responsive and Stop works. Python files are fetched from this folder,
// so the website always runs exactly the code in the repository.
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
importScripts(PYODIDE + 'pyodide.js');

const FILES = [
  'sim/__init__.py', 'sim/config.py', 'sim/settings.py', 'sim/events.py', 'sim/genes.py',
  'sim/memory.py', 'sim/decision.py', 'sim/analysis.py', 'sim/model.py', 'sim/runner.py',
  'explain.py', 'web/mesa_shim.py', 'web/bridge.py',
];

let py = null;
let cancelled = false;
const post = (type, data = {}) => self.postMessage({ type, ...data });
const call = (expr, arg) => { py.globals.set('_arg', arg); return py.runPython(expr); };

async function init(build) {
  post('status', { text: 'Loading Python (first visit downloads about 10 MB, then it is cached)…' });
  py = await loadPyodide({ indexURL: PYODIDE });
  post('status', { text: 'Loading numpy…' });
  await py.loadPackage('numpy');
  post('status', { text: 'Loading the simulation…' });
  const base = new URL('./', self.location.href);
  for (const f of FILES) {
    const res = await fetch(new URL(f, base).href + '?v=' + encodeURIComponent(build));
    if (!res.ok) throw new Error('could not load ' + f + ' (' + res.status + ')');
    const path = '/home/pyodide/world/' + f;
    py.FS.mkdirTree(path.slice(0, path.lastIndexOf('/')));
    py.FS.writeFile(path, await res.text());
  }
  py.runPython([
    'import sys',
    "sys.path.insert(0, '/home/pyodide/world'); sys.path.insert(0, '/home/pyodide/world/web')",
    'import mesa_shim',
    "sys.modules['mesa'] = mesa_shim",
    'import bridge',
  ].join('\n'));
  post('ready', { options: JSON.parse(py.runPython('bridge.options()')) });
}

async function run(params) {
  cancelled = false;
  const started = JSON.parse(call('bridge.start(_arg)', JSON.stringify(params)));
  if (started.error) { post('error', { text: started.error }); return; }
  post('started', started);
  let chunk = 5, done = false;
  while (!done && !cancelled) {
    const t0 = performance.now();
    const r = JSON.parse(py.runPython('bridge.advance(' + chunk + ')'));
    done = r.done;
    post('progress', r);
    // aim for about 120 ms per slice so the page can react in between
    const ms = performance.now() - t0;
    chunk = Math.max(1, Math.min(200, Math.round(chunk * (120 / Math.max(ms, 5)))));
    await new Promise((res) => setTimeout(res, 0));   // lets a Stop message in
  }
  post(cancelled ? 'stopped' : 'done', {
    map: py.runPython('bridge.final_map()'),
    summary: py.runPython('bridge.summary()'),
  });
}

self.onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.type === 'init') await init(m.build);
    else if (m.type === 'run') await run(m.params);
    else if (m.type === 'stop') cancelled = true;
    else if (m.type === 'explain') post('explain', { text: call('bridge.explain_cmd(_arg)', m.text) });
    else if (m.type === 'log') post('log', { text: py.runPython('bridge.log_jsonl()') });
  } catch (err) {
    post('error', { text: String(err && err.message || err) });
  }
};
