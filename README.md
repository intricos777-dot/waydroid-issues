# Waydroid Issues — Consolidated Report

**Host:** Garuda Linux / Arch-based  
**Kernel:** linux-zen 7.2.2-zen1-1-zen  
**Waydroid:** 1.6.3-1  
**LXC:** 1:7.0.0-2  
**Repo:** https://github.com/intricos777-dot/waydroid-issues

---

## Current Status

**Container:** STOPPED (unstable)  
**Session:** STOPPED  
**Host:** Stable, no boot regressions from investigation edits  
**Firewall:** Original state restored  
**LXC config:** Original state restored from backup

---

## Issues Found

### 1. Missing audio HAL in vendor image (Track A)
- **Severity:** High
- **Symptom:** `init: Could not start service 'vendor.audio-hal-2-0' ... Cannot find '/vendor/bin/hw/android.hardware.audio@2.0-service'`
- **Root cause:** Upstream packaging bug in `lineage_waydroid_x86_64` vendor image (`waydroid-image-gapps 20.0_20260428-1`). The vendor partition contains audio libraries for version 4.0 only (`android.hardware.audio@4.0.so`, `@4.0-impl.so`), but no `@2.0-service` binary or symlink.
- **Impact:** Audio HAL fails to start; affects both VANILLA and GAPPS system types.
- **Workaround:** Create symlink `android.hardware.audio@2.0-service` → `android.hardware.audio@4.0-impl.so` in vendor.img (caveat: version mismatch may cause functional issues).
- **Proper fix:** File upstream bug against Waydroid image build.
- **Status:** OpenCode investigating; workaround in progress.

### 2. LXC cgroup readonly errors (Track B)
- **Severity:** Medium
- **Symptom:** `libprocessgroup: Failed to make and chown /sys/fs/cgroup/uid_*: Read-only file system` and `init: createProcessGroup(...) failed for service ...`
- **Root cause:** LXC config mounts cgroup read-only (`lxc.mount.auto = cgroup:ro sys:ro proc`), preventing Android init from creating per-uid cgroup subtrees.
- **Impact:** Multiple services fail cgroup creation; task profiles cannot be applied.
- **Fix attempted:** `cgroup:delegate` failed on LXC 7.0.0 (`Invalid filesystem to automount`); `lxc.cgroup2.delegate = 1` not effective in current setup.
- **Status:** Config change not applied; needs upstream packaging fix.

### 3. DHCP blocked / IP address UNKNOWN (Track C)
- **Severity:** Low (network still works)
- **Symptom:** `waydroid status` shows `IP address: UNKNOWN`
- **Root cause:** nftables `DEVICE-GUARD` chain drops DHCP broadcasts from `waydroid0` before they reach dnsmasq. Lease file `/var/lib/misc/dnsmasq.waydroid0.leases` is 0 bytes.
- **Impact:** Status reporting only; container already has static IP `192.168.240.2`.
- **Fix attempted:** Added accept rules for UDP 67/68 on `waydroid0`, but traffic still blocked. Firewalld `trusted` zone assignment did not resolve.
- **Status:** Needs deeper firewall chain ordering fix or manual lease seeding.

### 4. rust_binder ENOSPC kernel regression (Track D)
- **Severity:** Critical
- **Symptom:** `rust_binder: Failed to allocate buffer. len:1056768, is_oneway:false` / `Failure in copy_transaction_data: ENOSPC`
- **Root cause:** Kernel `CONFIG_ANDROID_BINDER_IPC_RUST=y` with classic `CONFIG_ANDROID_BINDER_IPC` disabled. Known regression on Arch kernels ≥6.18.
- **Impact:** Large binder transactions fail; container instability, coredumps in `surfaceflinger` and `vendor.hwcomposer-2-1`.
- **Workaround:** Downgrade to kernel with classic binder or apply upstream patch `Darksonn/linux 8e28c67`.
- **Status:** No local runtime fix; requires kernel update or custom build.

---

## Additional Findings

- `lxc.hook.post-stop` exits 126 on shutdown (non-fatal but noisy)
- Container can reach RUNNING briefly, then stops due to combined cgroup/binder issues
- `waydroid session start` requires explicit `DBUS_SESSION_BUS_ADDRESS` and `XDG_RUNTIME_DIR`
- `/dev/binderfs` present with `anbox-binder`, `anbox-vndbinder`, `anbox-hwbinder`
- `/dev/ashmem` absent
- Wayland socket forwarding works (`/run/user/1000/wayland-0` mounted in container)

---

## Submission Targets

| Track | Target | Draft File |
|-------|--------|------------|
| A | https://github.com/waydroid/waydroid/issues/new | `submissions/track-a-waydroid-github.md` |
| B | https://bugs.archlinux.org | `submissions/track-b-arch-waydroid-bug.md` |
| C | https://forum.garudalinux.org | `submissions/track-c-garuda-firewall.md` |
| D | https://bugs.archlinux.org + Waydroid #2157 | `submissions/track-d-arch-kernel-bug.md` |

---

## Upstream References

- Waydroid issue #2157: https://github.com/waydroid/waydroid/issues/2157
- Arch bug #173: https://bugs.archlinux.org/task/173
- Darksonn/linux commit: https://github.com/Darksonn/linux/commit/8e28c67dc3f5c6fc77fd1a19f76fdca25f7c9c59

---

## Files

- `submissions/` — Ready-to-paste issue drafts
- `track-a-image-hal.md` — Detailed HAL investigation
- `track-b-cgroup.md` — cgroup readonly analysis
- `track-c-network.md` — DHCP/network diagnosis
- `track-d-kernel-regression.md` — Kernel regression report
- `FIX-REPORT.md` — OpenCode workaround attempts (in progress)

---

*Last updated: 2026-09-03*
