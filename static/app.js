// Commands are sent in order so a reset cannot be lost while a step is in flight.
let timer = null, target = 0, generation = 0, queue = Promise.resolve();
const $ = id => document.getElementById(id);
function render(s) {
  $('position').textContent = `(${s.x}, ${s.y})`;
  $('steps').textContent = s.steps;
  $('battery').textContent = s.battery + '%';
  $('distance').textContent = s.sensor.up + ' 格';
  $('message').textContent = s.message;
  const walls = new Set(s.walls.map(p => p.join(',')));
  const points = new Map(s.points.map((p, i) => [p.join(','), i + 1]));
  const path = new Set(s.path.map(p => p.join(',')));
  const map = $('map'); map.replaceChildren();
  for (let y = 0; y < s.height; y++) for (let x = 0; x < s.width; x++) {
    const key = `${x},${y}`, cell = document.createElement('div');
    cell.className = 'cell';
    if (walls.has(key)) cell.classList.add('wall');
    if (path.has(key)) cell.classList.add('path');
    if (points.has(key)) { cell.classList.add('point'); cell.textContent = points.get(key); }
    if (s.x === x && s.y === y) { cell.classList.add('robot'); cell.textContent = '◆'; }
    map.append(cell);
  }
}
function send(action) {
  const operation = queue.then(async () => {
    const response = await fetch('/api/action', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(action)});
    if (!response.ok) throw new Error('请求失败');
    const state = await response.json(); render(state); return state;
  });
  queue = operation.catch(() => {});
  return operation;
}
function stop() {
  generation++; clearTimeout(timer); timer = null;
  $('patrol').textContent = '▶ 开始自动巡检';
}
function reportError() { stop(); $('message').textContent = '连接失败，请检查服务是否运行'; }
async function tick(run) {
  try {
    const s = await send({action:'step', target});
    if (run !== generation) return;
    const p = s.points[target];
    if (s.x === p[0] && s.y === p[1]) {
      target++;
      if (target === s.points.length) {
        stop(); $('message').textContent = '巡检完成，已到达全部 3 个巡检点'; return;
      }
    } else if (s.message === '目标不可达') { stop(); return; }
    timer = setTimeout(() => tick(run), 450);
  } catch (_) { reportError(); }
}
$('patrol').onclick = () => {
  if (timer !== null) { stop(); return; }
  target = 0; const run = ++generation;
  timer = setTimeout(() => tick(run), 0);
  $('patrol').textContent = 'Ⅱ 停止巡检';
};
$('reset').onclick = () => { stop(); send({action:'reset'}).catch(reportError); };
function move(direction) { stop(); send({action:'move', direction}).catch(reportError); }
document.querySelectorAll('[data-dir]').forEach(b => b.onclick = () => move(b.dataset.dir));
document.addEventListener('keydown', e => {
  const direction = {ArrowUp:'up', ArrowDown:'down', ArrowLeft:'left', ArrowRight:'right'}[e.key];
  if (direction) { e.preventDefault(); if (!e.repeat) move(direction); }
});
fetch('/api/state').then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(render).catch(reportError);
