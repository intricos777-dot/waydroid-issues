# Waydroid IP Address UNKNOWN – Network Diagnosis

**Date:** 2026-09-03  
**Workdir:** /home/sin  
**Report:** /home/sin/waydroid-reports/track-c-network.md

## Observed Symptoms

- `waydroid status` shows `IP address: UNKNOWN`
- DHCP traffic visible in dmesg (client broadcast seen)
- Container is RUNNING
- Host interface `waydroid0` is UP at `192.168.240.1/24`
- dnsmasq is active on `waydroid0` with DHCP range `192.168.240.2-254`

## Findings

### 1. Lease File Is Empty (Primary Cause)

```
File: /var/lib/misc/dnsmasq.waydroid0.leases
Size: 0 bytes
Ownership: root:root, mode 0644
```

Waydroid's `get_device_ip_address()` (see `/usr/lib/waydroid/tools/helpers/net.py:43`) reads
the lease file and uses a regex to extract the IP:

```python
with open("/var/lib/misc/dnsmasq.waydroid0.leases") as f:
    match = re.search(r"(\d{1,3}\.){3}\d{1,3}\s", f.read())
    if match:
        return match.group().strip()
```

Because the file is empty, the function returns `None`, and `waydroid status` prints
`IP address: UNKNOWN`.  This is the direct reason for the reported symptom.

### 2. Container Already Has an IP Assigned

Inside the container (`waydroid shell`):

```
2: eth0@if30: ... inet 192.168.240.2/24 ... valid_lft forever preferred_lft forever
```

The container has `192.168.240.2`.  `valid_lft forever` suggests either a static
assignment inside the Android image or a stale lease.  Network connectivity exists:
the host ARP table also records `192.168.240.2` on `waydroid0`.

### 3. DHCP Traffic Is Blocked by DEVICE-GUARD

dmesg shows:

```
DEVICE-GUARD-BLOCK: IN=waydroid0 OUT= ... PROTO=UDP SPT=68 DPT=67
```

The nftables `ip filter` table contains a `DEVICE-GUARD` chain on the INPUT hook.
It accepts only traffic to/from `127.0.0.1` and the host Wi-Fi IP `10.245.106.176`;
everything else is logged and dropped.  The DHCP broadcast from the container
(`0.0.0.0 → 255.255.255.255`, src port 68) does **not** match any of those
accept rules and is dropped by this chain.

Because the DHCP Discover/Request never reaches the local dnsmasq process,
no lease is ever written to the lease file, and the file stays at 0 bytes.

### 4. Firewall Masquerade / Forwarding

Firewalld's `public` zone has:
- `target: DROP`
- `forward: yes`
- `masquerade: yes`

These settings are reasonable for NAT forwarding.  They are **not** the cause of
the lease-file issue.

### 5. dnsmasq Configuration

dnsmasq is started by waydroid with:

```
--dhcp-leasefile=/var/lib/misc/dnsmasq.waydroid0.leases
--listen-address 192.168.240.1
```

The lease file is open as fd 3 in the dnsmasq process, but it remains empty because
the DHCP replies never reach the client-side loop that writes leases.

## Root Cause

**`waydroid status` reads the IP exclusively from the dnsmasq lease file.**
The lease file is empty because:

1. **DEVICE-GUARD drops DHCP broadcasts** arriving on `waydroid0` in the host's
   INPUT chain before the local dnsmasq process can see them.
2. Without seeing DHCP requests, **dnsmasq cannot assign/write leases**.
3. The container still gets an IP via fallback/static config, so network works,
   but waydroid's status reporter has no lease entry to parse → `UNKNOWN`.

## Fix

### Option A – Allow DHCP through DEVICE-GUARD (preferred)

Add a rule to allow UDP port 67/68 traffic on `waydroid0` inside the DEVICE-GUARD
chain:

```bash
sudo nft add rule ip filter DEVICE-GUARD iifname "waydroid0" udp dport 67 accept
sudo nft add rule ip filter DEVICE-GUARD oifname "waydroid0" udp sport 67 accept
```

Then restart dnsmasq and trigger a DHCP renewal inside the container:

```bash
sudo waydroid container restart
# inside container:
sudo waydroid shell dhcpcd -n eth0
```

The lease file should populate and `waydroid status` will show the IP.

### Option B – Manually populate the lease file (quick workaround)

If firewall changes are undesirable, write a dummy lease entry that matches the
container's current state:

```
172800 00:16:3e:f9:d3:03 192.168.240.2 192.168.240.2 01:00:16:3e:f9:d3:03 *
```

Format: `<lease-time> <mac> <ip> <hostname> <client-id>`

After writing:

```bash
sudo systemctl restart dnsmasq
waydroid status   # should show 192.168.240.2
```

### Option C – Fix lease file ownership + restart dnsmasq

The lease file is currently `root:root 0644`.  Ensure dnsmasq can write to it:

```bash
sudo chown dnsmasq:dnsmasq /var/lib/misc/dnsmasq.waydroid0.leases
sudo chmod 644 /var/lib/misc/dnsmasq.waydroid0.leases
sudo systemctl restart dnsmasq
```

Note: This alone does **not** fix the DHCP-blocking problem; it only ensures that
if DHCP traffic ever reaches dnsmasq again, the lease file will be writable.

## Verification

```bash
waydroid status                        # should show IP address instead of UNKNOWN
cat /var/lib/misc/dnsmasq.waydroid0.leases   # should show a lease line
sudo waydroid shell ip addr show eth0         # should still show 192.168.240.2
dmesg | grep DEVICE-GUARD-BLOCK                # should no longer show DHCP blocks
```
