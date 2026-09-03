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
