# sysinfo-mcp-server

> **A Model Context Protocol (MCP) server that exposes live system metrics to Claude and other LLM clients.**

Ask Claude things like:
- *"What's my current CPU usage across all cores?"*
- *"Which 5 processes are eating the most memory right now?"*
- *"How much disk space is left on my root partition?"*
- *"Show me network I/O for eth0."*

---

## Features

| Tool | Description |
|---|---|
| `get_system_info` | OS, hostname, architecture, uptime, boot time |
| `get_cpu_info` | Per-core usage with ASCII bars, frequency, load averages |
| `get_memory_info` | RAM and swap — total, used, free, % |
| `get_disk_info` | All partitions or a specific path — usage with visual bars |
| `get_process_list` | Tabular process list, sortable by CPU / memory / PID / name |
| `get_network_info` | Per-interface bytes, packets, errors, IPv4/IPv6 addresses |
| `get_top_processes` | Ranked top-N processes by CPU or memory with RSS detail |

Works on **Windows, macOS, and Linux**.

---

## Requirements

- Python 3.10+
- [`mcp`](https://pypi.org/project/mcp/) >= 1.0.0
- [`psutil`](https://pypi.org/project/psutil/) >= 5.9.0

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/intruderfr/sysinfo-mcp-server.git
cd sysinfo-mcp-server

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Connect to Claude Desktop

1. Open your Claude Desktop config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Add the `sysinfo` server entry:

```json
{
  "mcpServers": {
    "sysinfo": {
      "command": "python",
      "args": ["C:/path/to/sysinfo-mcp-server/server.py"]
    }
  }
}
```

3. Restart Claude Desktop — the tools icon should show 7 new tools.

---

## Example conversations

```
You: What's using the most CPU on my machine right now?

Claude: [calls get_top_processes with resource="cpu", count=5]

## Top 5 Processes by CPU

1. chrome.exe (PID 4821)
   CPU: 18.4%  |  MEM: 3.21%  |  RSS: 512.0 MB  |  Status: running
```

```
You: How much disk space do I have left?

Claude: [calls get_disk_info]

## Disk Information

### C:\ (\\PhysicalDrive0)
- Filesystem: NTFS
- Total: 476.8 GB
- Used:  [████████████] 58.3% — 278.0 GB
- Free:  198.8 GB
```

---

## Tools reference

### `get_system_info`
Returns OS name, version, hostname, CPU counts, uptime, and boot time. No parameters.

### `get_cpu_info`
Returns per-core and overall CPU utilisation with ASCII progress bars, clock frequency, and load averages (Linux/macOS).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `interval` | float | 1 | Sampling window in seconds |

### `get_memory_info`
Returns RAM and swap — total, used, free, percentage. No parameters.

### `get_disk_info`
Returns usage for all mounted partitions, or a specific path.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `path` | string | all | Mount-point or directory to inspect |

### `get_process_list`
Returns a table of running processes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `sort_by` | string | cpu | cpu / memory / pid / name |
| `limit` | int | 20 | Max rows to return |

### `get_network_info`
Returns per-interface I/O counters and IP addresses.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `interface` | string | all | Filter to one interface |

### `get_top_processes`
Returns detailed info on the N most resource-hungry processes.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `resource` | string | cpu | cpu or memory |
| `count` | int | 10 | Number of processes |

---

## Project structure

```
sysinfo-mcp-server/
├── server.py                   # MCP server — all 7 tools defined here
├── requirements.txt            # Python dependencies
├── claude_desktop_config.json  # Example Claude Desktop config snippet
├── LICENSE                     # MIT
└── README.md
```

---

## License

MIT (c) 2026 [Aslam Ahamed](https://www.linkedin.com/in/aslam-ahamed/) — Head of IT @ Prestige One Developments, Dubai
