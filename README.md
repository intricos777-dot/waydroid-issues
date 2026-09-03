# Waydroid Issues — Consolidated Report

This repo tracks the Waydroid setup issues found on Garuda Linux / Arch with kernel linux-zen 7.2.2-zen1-1-zen, Waydroid 1.6.3-1, LXC 1:7.0.0-2.

## Submissions

### Track A — Missing audio HAL in vendor image
- **Target:** https://github.com/waydroid/waydroid/issues/new
- **Draft:** `track-a-waydroid-github.md`

```
[BUG] Vendor image missing android.hardware.audio@2.0-service on lineage_waydroid_x86_64

Description:
The current waydroid-image/vendor.img for lineage_waydroid_x86_64 is missing /vendor/bin/hw/android.hardware.audio@2.0-service. Android init fails with: "Could not start service 'vendor.audio-hal-2-0' ... Cannot find '/vendor/bin/hw/android.hardware.audio@2.0-service'". The vendor image only contains audio libs for version 4.0, with no @2.0-service binary or symlink. This affects both VANILLA and GAPPS system types because they share the same vendor.img.

Environment:
- Waydroid: 1.6.3-1
- Image package: waydroid-image-gapps 20.0_20260428-1
- Image build: lineage_waydroid_x86_64 (Apr 28 2026)
- Android version in vendor: 13 / SDK 33

Expected:
/vendor/bin/hw/android.hardware.audio@2.0-service exists in vendor.img.

Actual:
Binary is absent; audio HAL fails to start.

Suggested Fix:
Include the android.hardware.audio@2.0-service binary in vendor image builds, or add a symlink from the existing 4.0 implementation if ABI compatibility permits.

Logs:
init: Could not start service 'vendor.audio-hal-2-0' ... Cannot find '/vendor/bin/hw/android.hardware.audio@2.0-service'
```

### Track B — LXC cgroup readonly errors
- **Target:** https://bugs.archlinux.org
- **Draft:** `track-b-arch-waydroid-bug.md`

```
Subject: [waydroid] LXC config mounts cgroup read-only; Android init cgroup creation fails

Description:
On current Arch/Garuda builds with waydroid 1.6.3-1 and lxc 1:7.0.0-2, the LXC config uses:
  lxc.mount.auto = cgroup:ro sys:ro proc
This makes /sys/fs/cgroup read-only inside the container. Android init/libprocessgroup then fails with:
  libprocessgroup: Failed to make and chown /sys/fs/cgroup/uid_*: Read-only file system
  init: createProcessGroup(...) failed for service ...

Affected package: waydroid 1.6.3-1

Environment:
- Host: Garuda Linux / Arch-based
- Kernel: linux-zen 7.2.2-zen1-1-zen
- LXC: 1:7.0.0-2
- Waydroid: 1.6.3-1

Suggested Fix:
Change LXC config to use cgroup delegation instead of read-only mount, e.g.:
  lxc.mount.auto = cgroup:delegate sys:ro proc
or
  lxc.cgroup2.delegate = 1
Then restart waydroid-container.

Note: On LXC 7.0.0, "cgroup:delegate" may not be accepted by lxc-info; in that case use lxc.cgroup2.delegate = 1 explicitly.

Logs:
libprocessgroup: Failed to make and chown /sys/fs/cgroup/uid_1000: Read-only file system
init: createProcessGroup(1000, 3360) failed for service 'vendor.hwcomposer-2-1': Read-only file system
```

### Track C — DHCP blocked / IP UNKNOWN
- **Target:** https://forum.garudalinux.org + Arch Waydroid thread
- **Draft:** `track-c-garuda-firewall.md`

```
Subject: [Garuda] Waydroid IP address UNKNOWN / DHCP blocked by DEVICE-GUARD

Description:
Waydroid status shows "IP address: UNKNOWN" because the dnsmasq lease file is empty. Root cause: the nftables DEVICE-GUARD chain drops DHCP broadcasts from waydroid0 before they reach dnsmasq.

Symptoms:
- waydroid status: IP address: UNKNOWN
- /var/lib/misc/dnsmasq.waydroid0.leases: 0 bytes
- dmesg: DEVICE-GUARD-BLOCK for UDP 67/68 on waydroid0

Environment:
- Garuda Linux
- firewalld active
- nftables with DEVICE-GUARD chain
- waydroid 1.6.3-1

Suggested Fix:
Either:
1. Allow DHCP traffic through DEVICE-GUARD:
   nft add rule ip filter DEVICE-GUARD iifname "waydroid0" udp dport 67 accept
   nft add rule ip filter DEVICE-GUARD oifname "waydroid0" udp sport 67 accept
2. Or manually seed the lease file with container's current IP.

Workaround:
Container already has 192.168.240.2 assigned statically; network works, only status reporting is affected.
```

### Track D — rust_binder ENOSPC kernel regression
- **Target:** https://bugs.archlinux.org + Waydroid issue #2157
- **Draft:** `track-d-arch-kernel-bug.md`

```
Subject: [linux-zen] Waydroid rust_binder ENOSPC regression with CONFIG_ANDROID_BINDER_IPC_RUST

Description:
Kernels with CONFIG_ANDROID_BINDER_IPC_RUST=y and classic CONFIG_ANDROID_BINDER_IPC disabled cause Waydroid to encounter rust_binder ENOSPC failures for large transactions. This prevents stable Waydroid operation.

Exact dmesg:
rust_binder: Failed to allocate buffer. len:1056768, is_oneway:false
rust_binder: Failure in copy_transaction_data: ENOSPC
rust_binder: ... transaction to ... failed: ENOSPC

Environment:
- linux-zen 7.2.2-zen1-1-zen
- Waydroid 1.6.3-1
- CONFIG_ANDROID_BINDER_IPC_RUST=y
- # CONFIG_ANDROID_BINDER_IPC is not set

Working baseline:
- linux-zen 6.17.9-zen1-1 did not show this behavior

Upstream refs:
- Waydroid issue #2157
- Arch bug #173

Suggested Fix:
Backport or merge Darksonn/linux commit 8e28c67 to fix large binder transaction buffer allocation in rust_binder.

Workaround:
Downgrade to a kernel with classic binder until upstream patch is available.
```

## Links
- Waydroid issue #2157: https://github.com/waydroid/waydroid/issues/2157
- Arch bug #173: https://bugs.archlinux.org/task/173
- Darksonn/linux commit: https://github.com/Darksonn/linux/commit/8e28c67dc3f5c6fc77fd1a19f76fdca25f7c9c59

## Notes
- Host stability is intact; no boot regressions from investigation edits.
- LXC config and firewall have been restored to original state.
- Container is currently unstable due to combined cgroup/binder/image issues; upstream fixes required for stable operation.
