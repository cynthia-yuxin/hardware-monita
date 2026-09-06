"""Run an opt-in host agent, or the browser dashboard. Python 3.10+."""
import argparse
import ipaddress
import json
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from discovery import discover, network

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['agent','dashboard'])
    parser.add_argument('--subnet', help='Private IPv4 CIDR to discover (dashboard only)')
    parser.add_argument('--bind', default='127.0.0.1', help='Default: local browser only. Agent: use its LAN IP')
    parser.add_argument('--port', type=int, help='Agent default 8766; dashboard default 8765')
    parser.add_argument('--agent-port', type=int, default=8766)
    parser.add_argument('--exclude', action='append', default=[], help='IP to skip; repeat as needed')
    args = parser.parse_args()
    if args.mode == 'dashboard' and not args.subnet:
        parser.error('dashboard requires --subnet')
    if args.subnet:
        network(args.subnet)
    bind = ipaddress.ip_address(args.bind)
    if not bind.is_loopback:
        network(str(bind) + '/32')
    port = args.port or (8766 if args.mode == 'agent' else 8765)
    if not 1 <= port <= 65535 or not 1 <= args.agent_port <= 65535:
        parser.error('Port must be between 1 and 65535')
    state = {'protocol':'sakura-nvidia/1','timestamp':0,'hosts':[],'gpus':[]}
    lock = threading.Lock()
    def collect():
        nonlocal state
        if args.mode == 'agent':
            from telemetry import snapshot
        while True:
            started = time.monotonic()
            try:
                data = snapshot() if args.mode == 'agent' else {'hosts':discover(args.subnet,args.agent_port,args.exclude),'timestamp':time.time()}
                data['protocol'] = 'sakura-nvidia/1'
                with lock:
                    state = data
            except Exception:
                with lock:
                    state = dict(state, error='Collection failed; last sample retained')
            time.sleep(max(.2, (5 if args.mode == 'agent' else 10) - (time.monotonic()-started)))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            peer = ipaddress.ip_address(self.client_address[0])
            try:
                if not peer.is_loopback:
                    network(str(peer)+'/32')
            except ValueError:
                self.send_error(403); return
            path = self.path.split('?',1)[0]
            if path == ('/api/telemetry' if args.mode == 'agent' else '/api/snapshot'):
                with lock:
                    body = json.dumps(state,ensure_ascii=False).encode()
                mime = 'application/json; charset=utf-8'
            elif args.mode == 'dashboard' and path in ('/','/background.png'):
                file = ROOT/'web'/('index.html' if path == '/' else 'background.png')
                body = file.read_bytes()
                mime = 'text/html; charset=utf-8' if path == '/' else 'image/png'
            else:
                self.send_error(404); return
            self.send_response(200)
            self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers(); self.wfile.write(body)
        def log_message(self,*args):
            pass
    server = ThreadingHTTPServer((args.bind,port), Handler)
    threading.Thread(target=collect,daemon=True).start()
    print(f'{args.mode}: http://{args.bind}:{port}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
