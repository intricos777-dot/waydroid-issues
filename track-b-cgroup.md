# Waydroid CGroup Readonly Errors — Findings

## Problem
Container services fail with `Read-only file system` when attempting to create cgroup subtrees:
```
libprocessgroup: Failed to make and chown /sys/fs/cgroup/uid_*: Read-only file system
init: createProcessGroup(...) failed for service 'vendor.media.omx': Read-only file system
```

---

## Root Cause: CGroup Delegation Disabled

The Waydroid LXC config mounts the host cgroup filesystem **read-only** inside the container:

```ini
lxc.mount.auto = cgroup:ro sys:ro proc
```

This makes `/sys/fs/cgroup` read-only in the container. Android's `libprocessgroup` and `init` need to create per-uid cgroup subtrees (e.g. `/sys/fs/cgroup/uid_1000`) at runtime — this fails when the cgroup mount is read-only.

Additional evidence:
- Container is `FROZEN` (likely as a side effect).
- `lxc.payload.waydroid/cgroup.subtree_control` is **empty** — no controllers delegated to the container's subtree.
- `lxc.payload.waydroid/cgroup.type = domain` — the cgroup exists but is not delegated to the container.
- Missing files like `/dev/cpuset/foreground/tasks`, `/dev/stune/top-app/tasks` indicate Android-specific controllers are unavailable.

---

## Why `lxc.cgroup2.devices.allow` Does NOT Fix This

Adding:
```ini
lxc.cgroup2.devices.allow = c *:* rwm
```

grants device access to **character devices** (c *:*). That covers devices like `/dev/null`, `/dev/binder`, etc., but it does **not** grant write access to `/sys/fs/cgroup` or allow creating new cgroup directories. The error is `Read-only file system`, not `Permission denied` on a device node. This line would not solve the problem.

---

## Fix: Enable CGroup Delegation

Replace the read-only cgroup mount with a delegated, writable cgroup mount:

### Recommended Patch
In `/var/lib/waydroid/lxc/waydroid/config`, change:

```ini
lxc.mount.auto = cgroup:ro sys:ro proc
```

to:

```ini
lxc.mount.auto = cgroup:delegate sys:ro proc
```

`cgroup:delegate` mounts cgroup v2 writably and enables delegation for the container's subtree. LXC will write `+cpu +memory +pids +io` (and other available controllers) into `cgroup.subtree_control` automatically.

### Alternative Explicit Approach
If `cgroup:delegate` does not fully suffice, add after the `lxc.mount.auto` line:

```ini
lxc.cgroup2.delegate = 1
```

This tells LXC to explicitly delegate all controllers to the container subtree.

### After Applying the Patch
Restart Waydroid:
```bash
sudo systemctl restart waydroid-container
# or
waydroid stop && waydroid start
```

---

## Verification Steps
1. Check that the cgroup mount is writable in the container:
   ```bash
   waydroid shell ls -la /sys/fs/cgroup
   ```
2. Verify delegation is active:
   ```bash
   cat /sys/fs/cgroup/lxc.payload.waydroid/cgroup.subtree_control
   # should list: cpuset cpu io memory hugetlb pids ...
   ```
3. Check `journalctl` or container logs for absence of `Read-only file system` errors.

---

## Safety Note
- **Config change is safe**: `cgroup:delegate` is the standard Waydroid/LXC cgroup v2 configuration.
- Do **not** apply the `lxc.cgroup2.devices.allow = c *:* rwm` patch — it does not address the issue and is unnecessary.
- Always back up before editing: `sudo cp /var/lib/waydroid/lxc/waydroid/config /var/lib/waydroid/lxc/waydroid/config.bak`

---

## Status
- ✅ LXC config inspected.
- ✅ CGroup delegation status confirmed (disabled / read-only).
- ✅ Root cause identified: `cgroup:ro` mount prevents Android init from creating per-uid cgroups.
- ❌ Fix **not applied** — config modification deferred pending user confirmation.
- 📄 Report written to `/home/sin/waydroid-reports/track-b-cgroup.md`.
