#!/usr/bin/env python3
"""
mcp-server-sysinfo
==================
A Model Context Protocol (MCP) server that exposes live system information
to Claude and other LLM clients - CPU, memory, disk, processes, network.

Author: Aslam Ahamed - Head of IT @ Prestige One Developments, Dubai
LinkedIn: https://www.linkedin.com/in/aslam-ahamed/
License: MIT
"""

import asyncio
import platform
from datetime import datetime, timedelta
from typing import Any

import psutil
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
app = Server("sysinfo")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def bytes_to_human(n: int) -> str:
    """Convert a byte count to a human-readable string (e.g. 3.2 GB)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def bar(pct: float, width: int = 20) -> str:
    """Return an ASCII progress bar for the given percentage (0-100)."""
    filled = int(pct / 100 * width)
    return "#" * filled + "." * (width - filled)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------
TOOLS = [
    types.Tool(
        name="get_system_info",
        description=(
            "Return general system details: OS name/version, hostname, "
            "CPU core counts, uptime, and boot time."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_cpu_info",
        description=(
            "Return CPU utilisation (overall and per-core), clock frequency, "
            "and load averages on Linux/macOS."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "interval": {
                    "type": "number",
                    "description": "Sampling window in seconds (default: 1).",
                    "default": 1,
                }
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_memory_info",
        description="Return RAM and swap usage (total, used, free, percentage).",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    types.Tool(
        name="get_disk_info",
        description=(
            "Return disk usage for all mounted partitions, or for a specific "
            "path if supplied."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Specific mount-point or directory to inspect.",
                }
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_process_list",
        description=(
            "Return a table of running processes, optionally sorted by cpu, "
            "memory, pid, or name."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "sort_by": {
                    "type": "string",
                    "enum": ["cpu", "memory", "pid", "name"],
                    "description": "Sort field (default: cpu).",
                    "default": "cpu",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return (default: 20).",
                    "default": 20,
                },
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_network_info",
        description=(
            "Return network I/O counters (bytes sent/received, packet counts, "
            "errors) and IP addresses for each interface."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "interface": {
                    "type": "string",
                    "description": "Filter to a single interface (default: all).",
                }
            },
            "required": [],
        },
    ),
    types.Tool(
        name="get_top_processes",
        description=(
            "Return detailed info on the N processes consuming the most CPU or "
            "memory, including RSS, status, and owner."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "enum": ["cpu", "memory"],
                    "description": "Resource to rank by (default: cpu).",
                    "default": "cpu",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of processes to return (default: 10).",
                    "default": 10,
                },
            },
            "required": [],
        },
    ),
]


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return TOOLS


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------
@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent]:
    try:
        text = _dispatch(name, arguments)
    except Exception as exc:
        text = f"Error in {name}: {exc}"

    return [types.TextContent(type="text", text=text)]


def _dispatch(name: str, args: dict[str, Any]) -> str:
    if name == "get_system_info":
        return _system_info()
    if name == "get_cpu_info":
        return _cpu_info(float(args.get("interval", 1)))
    if name == "get_memory_info":
        return _memory_info()
    if name == "get_disk_info":
        return _disk_info(args.get("path"))
    if name == "get_process_list":
        return _process_list(args.get("sort_by", "cpu"), int(args.get("limit", 20)))
    if name == "get_network_info":
        return _network_info(args.get("interface"))
    if name == "get_top_processes":
        return _top_processes(args.get("resource", "cpu"), int(args.get("count", 10)))
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------------------
# Individual tool implementations
# ---------------------------------------------------------------------------
def _system_info() -> str:
    uname = platform.uname()
    boot_dt = datetime.fromtimestamp(psutil.boot_time())
    uptime = timedelta(seconds=int((datetime.now() - boot_dt).total_seconds()))

    lines = [
        "## System Information",
        "",
        f"- **Hostname**: {uname.node}",
        f"- **OS**: {uname.system} {uname.release}",
        f"- **Version**: {uname.version}",
        f"- **Architecture**: {uname.machine}",
        f"- **Processor**: {uname.processor or 'N/A'}",
        f"- **Python**: {platform.python_version()}",
        f"- **Physical CPU Cores**: {psutil.cpu_count(logical=False)}",
        f"- **Logical CPU Cores**: {psutil.cpu_count(logical=True)}",
        f"- **Boot Time**: {boot_dt.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **Uptime**: {uptime}",
    ]
    return "\n".join(lines)


def _cpu_info(interval: float) -> str:
    per_core = psutil.cpu_percent(interval=interval, percpu=True)
    overall = sum(per_core) / len(per_core)
    freq = psutil.cpu_freq()

    lines = [
        "## CPU Information",
        "",
        f"- **Overall Usage**: [{bar(overall)}] {overall:.1f}%",
        f"- **Physical Cores**: {psutil.cpu_count(logical=False)}",
        f"- **Logical Cores**: {psutil.cpu_count(logical=True)}",
    ]

    if freq:
        lines += [
            f"- **Current Frequency**: {freq.current:.0f} MHz",
            f"- **Min / Max**: {freq.min:.0f} / {freq.max:.0f} MHz",
        ]

    lines += ["", "### Per-Core Usage"]
    for i, pct in enumerate(per_core):
        lines.append(f"- Core {i:>2}: [{bar(pct)}] {pct:.1f}%")

    try:
        la = psutil.getloadavg()
        lines += [
            "",
            "### Load Average",
            f"- 1 min: **{la[0]:.2f}** | 5 min: **{la[1]:.2f}** | 15 min: **{la[2]:.2f}**",
        ]
    except AttributeError:
        pass  # Windows has no load average

    return "\n".join(lines)


def _memory_info() -> str:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    lines = [
        "## Memory Information",
        "",
        "### RAM",
        f"- **Total**: {bytes_to_human(mem.total)}",
        f"- **Used**: [{bar(mem.percent)}] {bytes_to_human(mem.used)} ({mem.percent:.1f}%)",
        f"- **Available**: {bytes_to_human(mem.available)}",
        f"- **Free**: {bytes_to_human(mem.free)}",
    ]
    if hasattr(mem, "buffers") and mem.buffers:
        lines.append(f"- **Buffers**: {bytes_to_human(mem.buffers)}")
    if hasattr(mem, "cached") and mem.cached:
        lines.append(f"- **Cached**: {bytes_to_human(mem.cached)}")

    lines += [
        "",
        "### Swap",
        f"- **Total**: {bytes_to_human(swap.total)}",
        f"- **Used**: [{bar(swap.percent)}] {bytes_to_human(swap.used)} ({swap.percent:.1f}%)",
        f"- **Free**: {bytes_to_human(swap.free)}",
    ]
    return "\n".join(lines)


def _disk_info(path):
    lines = ["## Disk Information", ""]

    def _partition_block(mountpoint, device="", fstype=""):
        try:
            usage = psutil.disk_usage(mountpoint)
            block = []
            header = f"### {mountpoint}"
            if device:
                header += f" ({device})"
            block.append(header)
            if fstype:
                block.append(f"- **Filesystem**: {fstype}")
            block += [
                f"- **Total**: {bytes_to_human(usage.total)}",
                f"- **Used**: [{bar(usage.percent)}] {bytes_to_human(usage.used)} ({usage.percent:.1f}%)",
                f"- **Free**: {bytes_to_human(usage.free)}",
                "",
            ]
            return block
        except PermissionError:
            return [f"### {mountpoint}: Permission denied", ""]
        except Exception as exc:
            return [f"### {mountpoint}: Error - {exc}", ""]

    if path:
        lines += _partition_block(path)
    else:
        for part in psutil.disk_partitions():
            lines += _partition_block(part.mountpoint, part.device, part.fstype)

    return "\n".join(lines)


def _process_list(sort_by: str, limit: int) -> str:
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    sort_keys = {
        "cpu": (lambda p: p.get("cpu_percent") or 0, True),
        "memory": (lambda p: p.get("memory_percent") or 0, True),
        "pid": (lambda p: p.get("pid") or 0, False),
        "name": (lambda p: (p.get("name") or "").lower(), False),
    }
    key_fn, reverse = sort_keys.get(sort_by, sort_keys["cpu"])
    procs.sort(key=key_fn, reverse=reverse)
    procs = procs[:limit]

    lines = [
        f"## Process List - sorted by {sort_by} (top {limit})",
        "",
        f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'STATUS':>10}  NAME",
        "-" * 60,
    ]
    for p in procs:
        lines.append(
            f"{p.get('pid', 0):>7}  "
            f"{p.get('cpu_percent') or 0:>6.1f}  "
            f"{p.get('memory_percent') or 0:>6.2f}  "
            f"{p.get('status', '?'):>10}  "
            f"{p.get('name', '?')}"
        )
    return "\n".join(lines)


def _network_info(interface):
    net_io = psutil.net_io_counters(pernic=True)
    net_addrs = psutil.net_if_addrs()

    lines = ["## Network Information", ""]
    ifaces = [interface] if interface else list(net_io.keys())

    for iface in ifaces:
        if iface not in net_io:
            lines += [f"### {iface}: Not found", ""]
            continue
        c = net_io[iface]
        lines += [
            f"### {iface}",
            f"- **Bytes Sent**: {bytes_to_human(c.bytes_sent)}",
            f"- **Bytes Recv**: {bytes_to_human(c.bytes_recv)}",
            f"- **Packets Sent**: {c.packets_sent:,}",
            f"- **Packets Recv**: {c.packets_recv:,}",
            f"- **Errors (in/out)**: {c.errin} / {c.errout}",
            f"- **Drops (in/out)**: {c.dropin} / {c.dropout}",
        ]
        for addr in net_addrs.get(iface, []):
            family = addr.family.name if hasattr(addr.family, "name") else str(addr.family)
            if "AF_INET" in family and "6" not in family:
                lines.append(f"- **IPv4**: {addr.address} (mask: {addr.netmask})")
            elif "AF_INET6" in family:
                lines.append(f"- **IPv6**: {addr.address}")
            elif "AF_PACKET" in family or "AF_LINK" in family:
                lines.append(f"- **MAC**: {addr.address}")
        lines.append("")

    return "\n".join(lines)


def _top_processes(resource: str, count: int) -> str:
    field = "cpu_percent" if resource == "cpu" else "memory_percent"
    procs = []
    for p in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent", "memory_info", "status", "username"]
    ):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    procs.sort(key=lambda p: p.get(field) or 0, reverse=True)
    procs = procs[:count]

    lines = [f"## Top {count} Processes by {resource.upper()}", ""]
    for i, p in enumerate(procs, 1):
        rss = ""
        if p.get("memory_info"):
            rss = f" | RSS: {bytes_to_human(p['memory_info'].rss)}"
        lines += [
            f"**{i}. {p.get('name', '?')}** (PID {p.get('pid', 0)})",
            f"   CPU: {p.get('cpu_percent') or 0:.1f}%  |  "
            f"MEM: {p.get('memory_percent') or 0:.2f}%{rss}  |  "
            f"Status: {p.get('status', '?')}  |  "
            f"User: {p.get('username', '?')}",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sysinfo",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
