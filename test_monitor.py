import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import discovery
import telemetry

class Tests(unittest.TestCase):
    def test_scope(self):
        for cidr in ['8.8.8.0/24','0.0.0.0/0','192.168.0.0/16','::1/128']:
            with self.assertRaises(ValueError): discovery.network(cidr)
        self.assertEqual(str(discovery.network('192.168.1.9/24')),'192.168.1.0/24')
        with patch.object(discovery,'inspect',return_value=None) as probe:
            discovery.discover('192.168.1.0/30',exclude=['192.168.1.1'])
            self.assertEqual([c.args[0] for c in probe.call_args_list],['192.168.1.2'])

    def test_protocol(self):
        payload={'protocol':'sakura-nvidia/1','gpus':[{'name':'Fixture GPU'}]}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(payload).encode())
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.assertEqual(len(discovery.inspect('127.0.0.1',server.server_port)['gpus']),1)
            payload['protocol']='unrelated-service'
            self.assertIsNone(discovery.inspect('127.0.0.1',server.server_port))
        finally:server.shutdown();server.server_close()

    def test_unsupported_metrics_and_processes(self):
        self.assertIsNone(telemetry.number('[N/A]'))
        def query(fields,kind='gpu'):
            if kind=='compute-apps':return [['GPU-1','12','/private/path/worker','1024']]
            return [['0','GPU-1','Fixture','1024','4096','0','N/A','200','42']]
        with patch.object(telemetry,'query',side_effect=query),patch.object(telemetry.subprocess,'run',side_effect=FileNotFoundError):
            sample=telemetry.snapshot()
            self.assertEqual(sample['gpus'][0]['used'],1024)
            self.assertIsNone(sample['gpus'][0]['power'])
            self.assertEqual(sample['gpus'][0]['apps'][0]['name'],'worker')

class ServerTests(unittest.TestCase):
    def test_dashboard_http_and_private_files(self):
        import subprocess, socket, sys, time, urllib.request, urllib.error
        from pathlib import Path
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        process=subprocess.Popen([sys.executable,'server.py','dashboard','--subnet','192.168.1.0/30','--exclude','192.168.1.1','--exclude','192.168.1.2','--port',str(port)],cwd=Path(__file__).parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        base=f'http://127.0.0.1:{port}'
        try:
            for attempt in range(50):
                try:
                    response=opener.open(base+'/api/snapshot',timeout=.5);break
                except OSError:time.sleep(.1)
            else:self.fail('Dashboard did not start')
            self.assertEqual(json.load(response)['hosts'],[])
            self.assertIn('显卡观察室',opener.open(base).read().decode())
            for path in ['/server.py','/../telemetry.py','/.git/config','/api/telemetry']:
                with self.assertRaises(urllib.error.HTTPError) as error:opener.open(base+path)
                self.assertEqual(error.exception.code,404)
            with self.assertRaises(urllib.error.HTTPError) as error:opener.open(urllib.request.Request(base+'/api/snapshot',data=b'{}'))
            self.assertEqual(error.exception.code,501)
        finally:
            process.terminate();process.wait(timeout=5)

if __name__=='__main__':unittest.main()
