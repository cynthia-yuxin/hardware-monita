# Hardware Monita 🌸

粉色、半透明、手机优先的局域网显卡观察室。

![樱花河畔背景](web/background.png)
只保留设备监控，不包含原项目的登录、账号权限、推理健康、P0 告警、笔记本电池或业务服务。

## 显示什么

- 已响应的 NVIDIA 主机数，以及显卡总数（多卡主机会逐卡显示）
- 每台主机的 CPU 使用率、RAM 使用率与总容量
- 每张显卡的大号已用显存、小号总显存、显存比例
- GPU 使用率、温度、功率、应用名称、PID、进程显存
- 不支持的指标显示 `—`，过期数据标记为历史数据

## 启动

需要 Python 3.10+，NVIDIA 主机需安装驱动并能运行 `nvidia-smi`。Linux CPU/RAM 直接读取 `/proc`，无需额外依赖；Windows 使用 `psutil`；图形进程 `pmon` 在部分驱动/Windows 上不可用，会明确提示。

```sh
python -m pip install -r requirements.txt
```

在每台希望被发现的 NVIDIA 主机上启动采集器，把地址换成该主机自己的 LAN IP：

```sh
python server.py agent --bind 192.168.1.20
```

在观看监控的电脑启动界面，子网换成你实际使用的私有局域网：

```sh
python server.py dashboard --subnet 192.168.1.0/24
```

打开 http://127.0.0.1:8765 。需要让同一局域网的手机观看时，增加 `--bind` 并使用运行界面的电脑的 LAN IP：

```sh
python server.py dashboard --subnet 192.168.1.0/24 --bind 192.168.1.10
```

采集端口默认 8766，界面端口默认 8765，可用 `--port` 修改；界面的 `--agent-port` 必须与采集器一致。防火墙只向可信局域网开放所需端口。`--exclude IP` 可以重复使用，跳过不应探测的地址。

## “自动发现”的准确含义

没有免认证的通用协议能仅凭网络地址列出所有 NVIDIA 硬件。本项目每 10 秒尝试访问指定子网中采集器的固定 HTTP 端口，最多 32 个并发，子网最多 1024 个地址。它不扫描其他端口、不尝试 SSH 登录、不安装远程软件、不跟随重定向。只有返回正确协议且有显卡的主机会计数；机器离线、未运行采集器或被防火墙阻挡时不会被发现。采集器每 5 秒更新，页面每 5 秒读取最近结果。

## 模块

- `telemetry.py`：独立 CPU/RAM/NVIDIA JSON 采集，`python telemetry.py` 可直接使用。
- `discovery.py`：有界子网发现，`discover(cidr, port, exclude)` 返回已发现主机。
- `server.py` + `web/index.html`：只读 HTTP 服务和无框架界面。

只用于可信局域网：未内置登录或 TLS，任何能连接采集端口的人都可读取设备与进程指标。不要将端口直接转发到公网。默认绑定 loopback；显式指定 LAN IP 才对局域网提供服务。

## 验证

```sh
python -m unittest -v test_monitor.py
python -m py_compile telemetry.py discovery.py server.py
```

已有环境之外的 Windows/MIG 驱动组合仍需实际硬件验收，不能把不支持的指标当成 0。`compute-apps` 与可用的 `pmon` 合并显示；不读取命令行参数或应用私有路径。

## 背景与许可

保留当前观察室的樱花河畔人物背景。背景为用户授权公开的 AI 生成插画；六张原始照片不包含在仓库中。代码及随仓库分发的背景采用 MIT 许可。仅发布这个目录，不要将相邻的部署目录、监控快照、SSH 配置或私有业务代码加入仓库。
