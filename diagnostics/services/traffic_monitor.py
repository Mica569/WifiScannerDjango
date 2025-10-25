import time
from typing import Dict, List, Optional

try:
    from scapy.all import sniff
    from scapy.layers.inet import IP
except Exception:  # scapy may be unavailable or lack permissions
    sniff = None  # type: ignore
    IP = None  # type: ignore

import psutil


def _local_ipv4_addresses() -> List[str]:
    addrs = []
    for if_addrs in psutil.net_if_addrs().values():
        for addr in if_addrs:
            if getattr(addr, 'family', None) == getattr(psutil, 'AF_LINK', object()):
                continue
            if getattr(addr, 'family', None) == 2:  # socket.AF_INET, but avoid import
                if addr.address and not addr.address.startswith('169.254.'):
                    addrs.append(addr.address)
    return addrs


def sample_bandwidth(duration_sec: int = 5, iface: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """
    Capture traffic for a short window and estimate per-remote-IP bandwidth.

    Returns a dict keyed by remote ip with fields:
      - bytes_in: bytes received from that IP
      - bytes_out: bytes sent to that IP
    Values are totals over the capture window (duration_sec).
    """
    results: Dict[str, Dict[str, float]] = {}

    local_ips = set(_local_ipv4_addresses())

    if sniff is None or IP is None:
        return results

    start = time.time()

    def _accumulate(pkt):
        try:
            if IP not in pkt:
                return
            ip_layer = pkt[IP]
            src = ip_layer.src
            dst = ip_layer.dst
            plen = int(len(pkt))

            # Determine direction relative to local host
            if src in local_ips and dst not in local_ips:
                # outbound to remote dst
                r = results.setdefault(dst, {"bytes_in": 0.0, "bytes_out": 0.0})
                r["bytes_out"] += plen
            elif dst in local_ips and src not in local_ips:
                # inbound from remote src
                r = results.setdefault(src, {"bytes_in": 0.0, "bytes_out": 0.0})
                r["bytes_in"] += plen
        except Exception:
            # Best-effort only
            pass

    try:
        sniff(filter="ip", prn=_accumulate, store=False, timeout=duration_sec, iface=iface)
    except Exception:
        # Could be missing permissions/drivers; return empty to signal N/A
        return {}

    # Make sure at least duration is non-zero to avoid div by zero later
    elapsed = max(0.001, time.time() - start)
    # Attach elapsed for callers that want Mbps computation
    for v in results.values():
        v["_elapsed"] = elapsed
    return results


def as_mbps(sample: Dict[str, Dict[str, float]]) -> List[Dict[str, float]]:
    """Convert sampled byte totals into Mbps for each remote IP."""
    out: List[Dict[str, float]] = []
    elapsed = 0.0
    for v in sample.values():
        if "_elapsed" in v:
            elapsed = v["_elapsed"]
            break
    if elapsed <= 0:
        elapsed = 1.0
    for ip, v in sample.items():
        bytes_in = float(v.get("bytes_in", 0.0))
        bytes_out = float(v.get("bytes_out", 0.0))
        out.append({
            "ip": ip,
            "download_mbps": round((bytes_in * 8.0) / elapsed / 1_000_000, 3),
            "upload_mbps": round((bytes_out * 8.0) / elapsed / 1_000_000, 3),
        })
    # Sort by total usage desc
    out.sort(key=lambda x: (x["download_mbps"] + x["upload_mbps"]), reverse=True)
    return out

