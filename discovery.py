"""Bounded discovery of opt-in Sakura agents, never arbitrary SSH hosts."""
import concurrent.futures
import ipaddress
import json
import urllib.request

MAX_RESPONSE = 2 * 1024 * 1024

def network(value):
    net = ipaddress.ip_network(value, strict=False)
    ranges = [ipaddress.ip_network(x) for x in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')]
    if net.version != 4 or net.num_addresses > 1024 or not any(net.subnet_of(r) for r in ranges):
        raise ValueError('Use a private IPv4 subnet with at most 1024 addresses')
    return net

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def inspect(host, port=8766):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(f'http://{host}:{port}/api/telemetry', timeout=2) as response:
            raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                return None
            data = json.loads(raw)
        if data.get('protocol') != 'sakura-nvidia/1' or not isinstance(data.get('gpus'), list):
            return None
        if not data['gpus']:
            return None
        return dict(data, address=host)
    except (OSError, ValueError, TypeError, AttributeError):
        return None

def discover(subnet, port=8766, exclude=()):
    addresses = [str(ip) for ip in network(subnet).hosts() if str(ip) not in exclude]
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        return [result for result in pool.map(lambda host: inspect(host, port), addresses) if result]
