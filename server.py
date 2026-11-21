import json
import os
import threading
from pathlib import Path
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

WIDTH, HEIGHT = 12, 8
WALLS = {(4,y) for y in range(6) if y != 3} | {(8,y) for y in range(2,8) if y != 5} | {(x,1) for x in range(6,9)}
POINTS = [(2, 5), (6, 3), (10, 6)]
lock = threading.Lock()
state = {"x": 1, "y": 1, "steps": 0, "message": "准备就绪", "target": None}

def route(start, goal):
    queue = deque([start]); previous = {start: None}
    while queue:
        point = queue.popleft()
        if point == goal: break
        for dx, dy in [(0,-1),(1,0),(0,1),(-1,0)]:
            nxt = (point[0]+dx, point[1]+dy)
            if 0 <= nxt[0] < WIDTH and 0 <= nxt[1] < HEIGHT and nxt not in WALLS and nxt not in previous:
                previous[nxt] = point; queue.append(nxt)
    if goal not in previous: return []
    path = []
    while goal != start:
        path.append(goal); goal = previous[goal]
    return list(reversed(path))

def snapshot():
    # Four simulated proximity readings: count free grid cells until a wall or edge.
    distances = {}
    for name, (dx, dy) in {'up': (0,-1), 'right': (1,0), 'down': (0,1), 'left': (-1,0)}.items():
        x, y, distance = state['x'], state['y'], 0
        while True:
            x += dx; y += dy
            if not (0 <= x < WIDTH and 0 <= y < HEIGHT) or (x, y) in WALLS: break
            distance += 1
        distances[name] = distance
    battery = max(0, 100 - state['steps'])
    return {**state, "width": WIDTH, "height": HEIGHT, "walls": sorted(WALLS), "points": POINTS,
            "sensor": distances, "battery": battery,
            "path": route((state['x'], state['y']), POINTS[state['target']]) if state['target'] is not None else []}

def action(data):
    kind = data.get('action')
    if kind == 'reset':
        state.update(x=1,y=1,steps=0,message='已重置',target=None)
    elif kind == 'move':
        directions = {'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}
        if not isinstance(data.get('direction'), str) or data['direction'] not in directions: raise ValueError('无效方向')
        dx,dy = directions[data['direction']]; x,y = state['x']+dx,state['y']+dy
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT) or (x,y) in WALLS:
            state['message'] = '前方有障碍或地图边界'; state['target'] = None
        else:
            state.update(x=x,y=y,steps=state['steps']+1,message='移动成功',target=None)
    elif kind == 'step':
        target = data.get('target')
        if type(target) is not int or not 0 <= target < len(POINTS): raise ValueError('无效巡检点')
        goal = POINTS[target]; path = route((state['x'],state['y']),goal)
        if path:
            state.update(x=path[0][0],y=path[0][1],steps=state['steps']+1,target=target,message='正在前往巡检点')
        elif (state['x'],state['y']) != goal: state['message'] = '目标不可达'
        if (state['x'],state['y']) == goal: state['message'] = '已到达巡检点'; state['target'] = target
    else: raise ValueError('无效操作')
    return snapshot()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(Path(__file__).resolve().parent / 'static'),**kwargs)
    def reply(self,code,data):
        body=json.dumps(data,ensure_ascii=False).encode(); self.send_response(code); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if self.path == '/api/state':
            with lock: self.reply(200,snapshot())
        else: super().do_GET()
    def do_POST(self):
        if self.path != '/api/action': self.reply(404,{'error':'未找到接口'}); return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 1024: raise ValueError('请求长度无效')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('请求格式无效')
            with lock: result=action(data)
            self.reply(200,result)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError): self.reply(400,{'error':'请求无效'})

if __name__ == '__main__':
    port=int(os.environ.get('PORT','8000')); print(f'http://localhost:{port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
