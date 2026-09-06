"""Read-only NVIDIA, CPU and RAM telemetry. No application-specific probes."""
import csv
import io
import json
import pathlib
import subprocess
import time
import socket


def query(fields, kind='gpu'):
    p = subprocess.run(['nvidia-smi', '--query-' + kind + '=' + fields,
                        '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
    if p.returncode:
        raise RuntimeError('nvidia-smi unavailable')
    return list(csv.reader(io.StringIO(p.stdout), skipinitialspace=True))


def number(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def system_metrics():
    if pathlib.Path('/proc/stat').exists():
        def cpu():
            values = list(map(int, pathlib.Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
            return sum(values), values[3] + values[4]
        before = cpu(); time.sleep(.35); after = cpu()
        mem = {line.split(':')[0]: int(line.split()[1]) for line in pathlib.Path('/proc/meminfo').read_text().splitlines()}
        return round(100*(1-(after[1]-before[1])/max(1,after[0]-before[0])),1), round(100*(1-mem['MemAvailable']/mem['MemTotal']),1), round(mem['MemTotal']/1048576,1)
    import psutil
    memory = psutil.virtual_memory()
    return psutil.cpu_percent(interval=.35), memory.percent, round(memory.total/1024**3,1)


def snapshot():
    cpu, memory, ram = system_metrics()
    result = {'hostname': socket.gethostname(), 'cpu': cpu, 'memory': memory,
              'ram_gb': ram, 'timestamp': time.time(), 'gpus': []}
    try:
        apps = {}
        try:
            for uuid, pid, name, used in query('gpu_uuid,pid,process_name,used_gpu_memory', 'compute-apps'):
                apps.setdefault(uuid, []).append({'pid': pid, 'name': pathlib.PurePath(name.replace('\\','/')).name, 'memory': number(used)})
            result['apps_ok'] = True
        except Exception:
            result['apps_ok'] = False
        for row in query('index,uuid,name,memory.used,memory.total,utilization.gpu,power.draw,power.limit,temperature.gpu'):
            idx, uuid, name, used, total, util, power, limit, temp = row
            result['gpus'].append(dict(index=idx, name=name, used=number(used), total=number(total),
                                       util=number(util), power=number(power), limit=number(limit),
                                       temp=number(temp), apps=apps.get(uuid, [])))
        # pmon also includes graphics processes; compute-apps supplies full names and paths.
        result['graphics_ok'] = False
        p = subprocess.run(['nvidia-smi','pmon','-c','1','-s','m'],capture_output=True,text=True,timeout=4)
        result['graphics_ok'] = p.returncode == 0 and 'Not Supported' not in p.stdout
        if result['graphics_ok']:
            for line in p.stdout.splitlines():
                cols = line.split()
                if len(cols) < 6 or not cols[0].isdigit() or not cols[1].isdigit():
                    continue
                for g in result['gpus']:
                    if g['index'] == cols[0] and not any(a['pid'] == cols[1] for a in g['apps']):
                        g['apps'].append({'pid':cols[1],'name':cols[-1],'memory':number(cols[3])})
    except Exception:
        result['gpu_error'] = 'GPU telemetry unavailable'
    return result


if __name__ == "__main__":
    print(json.dumps(snapshot()))
