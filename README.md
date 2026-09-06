# Hardware Monita 🌸

**轻量的局域网 NVIDIA 硬件监控面板。**

发现局域网中运行采集器的 NVIDIA 主机，集中查看显存、GPU、CPU 和内存状态。樱花主题、半透明卡片与响应式布局，让多台工作站的运行情况在电脑和手机上都清晰可见。

[快速开始](#快速开始) · [配置](#配置) · [工作原理](#工作原理) · [常见问题](#常见问题)

## 功能

- **多主机、多显卡**：统计已发现的 NVIDIA 主机与显卡数量，逐卡展示指标。
- **显存优先**：突出已用显存，同时显示总容量、占用比例和进度条。
- **运行状态**：GPU 利用率、温度、功率，以及主机 CPU 使用率、RAM 使用率和总容量。
- **进程信息**：应用名称、PID、进程显存；在驱动支持时合并计算与图形进程。
- **手机适配**：响应式卡片、可调透明度、自动刷新与过期数据提示。
- **轻量部署**：Python HTTP 服务与原生 HTML/CSS/JavaScript，无前端构建步骤。

<details>
<summary>樱花主题背景</summary>

![Hardware Monita 樱花河畔主题背景](web/background.png)

</details>

## 环境要求

| 组件 | 要求 |
| --- | --- |
| Python | 3.10 或更高版本 |
| NVIDIA 主机 | 已安装驱动，`nvidia-smi` 可在命令行运行 |
| Linux 采集 | CPU/RAM 直接读取 `/proc` |
| Windows 采集 | CPU/RAM 通过 `psutil` 获取 |
| 浏览器 | 支持现代 JavaScript 的 Chrome、Edge、Firefox 或 Safari |
| 网络 | 采集器与面板之间可访问的私有 IPv4 局域网 |

## 快速开始

### 1. 下载与安装

在运行采集器或面板的电脑上下载项目：

```bash
git clone https://github.com/cynthia-yuxin/hardware-monita.git
cd hardware-monita
python -m pip install -r requirements.txt
```

也可通过仓库页面的 **Code → Download ZIP** 下载并解压。

以下示例使用 `192.168.1.0/24` 网段，请替换为实际网络地址。

### 2. 启动主机采集器

在每台需要监控的 NVIDIA 主机上执行，`--bind` 指定该主机的局域网 IP：

```bash
python server.py agent --bind 192.168.1.20
```

保持进程运行，并允许可信局域网访问该主机的 TCP **8766** 端口。

### 3. 启动监控面板

在用于查看监控的电脑上执行：

```bash
python server.py dashboard --subnet 192.168.1.0/24
```

打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)。面板会自动发现指定网段中已启动、可连通且报告 NVIDIA 显卡的采集器。

采集器和面板可以运行在同一台电脑上。按 `Ctrl+C` 停止相应进程。

### 4. 在手机上查看

让面板绑定到所在电脑的局域网 IP：

```bash
python server.py dashboard --subnet 192.168.1.0/24 --bind 192.168.1.10
```

允许可信局域网访问 TCP **8765**，然后使用同一网络内的手机打开 `http://192.168.1.10:8765`。

## 配置

```bash
python server.py --help
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `mode` | 必填 | `agent` 采集主机指标；`dashboard` 提供监控面板 |
| `--bind` | `127.0.0.1` | 监听地址；对局域网提供服务时填写本机私有 IPv4 地址 |
| `--port` | agent：`8766`；dashboard：`8765` | 当前服务的监听端口 |
| `--subnet` | 无 | 发现范围，例如 `192.168.1.0/24`；dashboard 模式必填 |
| `--agent-port` | `8766` | 面板发现采集器时使用的端口 |
| `--exclude` | 无 | 跳过指定 IP，可重复使用 |

自定义采集端口时，面板需使用相同的 `--agent-port`：

```bash
# NVIDIA 主机
python server.py agent --bind 192.168.1.20 --port 9876

# 监控面板
python server.py dashboard --subnet 192.168.1.0/24 --agent-port 9876 --exclude 192.168.1.50
```

## 工作原理

```text
NVIDIA 主机                         监控面板                    浏览器
nvidia-smi + CPU/RAM → Agent  →  局域网发现与聚合  →  显卡与主机卡片
                      :8766          :8765
```

采集器每约 **5 秒**更新一次指标。面板在指定子网内访问采集器的固定端口，按约 **10 秒**的周期发现主机；一次发现耗时较长时，以实际完成时间为准。浏览器每 **5 秒**读取最新聚合结果。

发现功能仅计入返回项目协议且包含显卡的主机。未安装采集器、离线或被防火墙阻挡的设备不会计入，因此发现结果不等于局域网全部 NVIDIA 硬件的数量。

发现范围限定为 RFC 1918 私有 IPv4 子网，每次最多 **1024 个地址、32 个并发连接**。请求不跟随重定向。

## 模块与接口

| 文件 | 职责 |
| --- | --- |
| `telemetry.py` | 采集 CPU、RAM、显卡及进程信息 |
| `discovery.py` | 有界子网发现与协议识别 |
| `server.py` | 采集器与面板的只读 HTTP 服务 |
| `web/index.html` | 监控界面 |
| `web/background.png` | 樱花主题背景 |
| `test_monitor.py` | 自动化测试 |

单独输出本机指标：

```bash
python telemetry.py
```

HTTP 接口：

| 服务 | 路径 | 返回内容 |
| --- | --- | --- |
| Agent | `GET /api/telemetry` | 单台主机的指标快照 |
| Dashboard | `GET /api/snapshot` | 已发现主机的聚合快照 |

## 常见问题

### 面板没有发现设备

1. 在目标主机运行 `nvidia-smi`，确认驱动可用。
2. 确认采集器绑定到该主机的局域网 IP，而非默认的 `127.0.0.1`。
3. 确认 `--subnet` 包含目标地址，且 `--agent-port` 与采集端口一致。
4. 检查防火墙、访客 Wi-Fi 或无线客户端隔离是否阻止连接。

可从面板电脑访问 `http://目标主机IP:8766/api/telemetry` 检查连通性。

### 部分指标显示 `—`

驱动、显卡型号或运行模式可能不支持某些查询。不支持的数值以 `—` 展示，不视为零。

### 没有图形进程信息

进程列表来自 `nvidia-smi --query-compute-apps` 和可用的 `nvidia-smi pmon`。部分 Windows、驱动或 MIG 环境不支持全部指标；具体覆盖范围取决于设备与驱动能力。

### 能否部署到公网？

当前版本面向可信局域网，未内置身份认证或 TLS。任何能够连接服务端口的客户端都可以读取相应硬件与进程指标。请限制防火墙访问范围，不要直接将服务端口转发到公网。

## 开发

```bash
python -m unittest -v test_monitor.py
python -m py_compile telemetry.py discovery.py server.py
```

测试覆盖子网范围与排除规则、发现协议识别、指标解析，以及 HTTP 路由和私有文件访问限制。

欢迎通过 [Issues](https://github.com/cynthia-yuxin/hardware-monita/issues) 提交问题，或通过 Pull Request 贡献改进。涉及硬件兼容性的问题，请附上操作系统、驱动版本、GPU 型号和脱敏后的错误信息。

## 许可证

- **代码与文档**：[MIT](LICENSE)。
- **主题背景 `web/background.png`**：[CC BY-ND 4.0（署名—禁止演绎）](https://creativecommons.org/licenses/by-nd/4.0/deed.zh-hans)。署名为 **cynthia-yuxin**；允许按许可条款分享原图，不得分发改编后的图像。详见[背景图片许可](web/background.LICENSE.md)。
