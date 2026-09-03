# Kernel Regression Report: Waydroid rust_binder ENOSPC

**Host:** Linux 7.2.2-zen1-1-zen (Garuda Linux, Arch-based)  
**Waydroid:** 1.6.3-1  
**Upstream refs:** Arch bug #173, Waydroid issue #2157  
**Proposed upstream fix:** Darksonn/linux commit `8e28c67`

## Kernel Version

```
7.2.2-zen1-1-zen
```

## Exact dmesg Lines

```
[ 3909.318192] rust_binder: Failed to allocate buffer. len:1056768, is_oneway:false
[ 3909.318200] rust_binder: Failure in copy_transaction_data: ENOSPC
[ 3909.318203] rust_binder: 236122:236482 transaction to 235681 failed: ENOSPC
```

## Kernel Config

```
CONFIG_ANDROID_BINDER_IPC_RUST=y
# CONFIG_ANDROID_BINDER_IPC is not set
```

## Comparison to Working Kernels (e.g., 6.17.9)

- On linux-zen ≤6.17.x (and other kernels using the classic C binder, or the `CONFIG_ANDROID_BINDER_IPC` driver), Waydroid sessions start and the container remains `RUNNING`.
- With the Rust binder driver enabled as the sole implementation, transactions involving large oneway buffers (>1 MB) fail with `ENOSPC`, causing HALs and core services to abort, the container to stop, and `waydroid status` to show `STOPPED`.
- This behavior is absent on working kernels, confirming it is a regression introduced in the rust_binder code path (enabled in Arch kernels ≥6.18, including 7.2.2-zen).

## Bug Tracker References

- **Arch bug #173**: https://bugs.archlinux.org/task/173  
- **Waydroid issue #2157**: https://github.com/waydroid/waydroid/issues/2157  

## Suggested Patch Direction

Upstream fix: **Darksonn/linux commit `8e28c67`** — properly handles large binder transactions in `copy_transaction_data` so that buffer allocation does not fail spuriously with `ENOSPC` when a large oneway buffer is requested. Backporting or cherry-picking this commit into linux-zen resolves the regression for Waydroid.

## Known Workarounds

| Method | Details | Caveat |
|--------|---------|--------|
| Boot param | None identified | — |
| Sysctl | None exposed for rust_binder | — |
| Module param | `rust_devices` only (device list) | Not a fix; controls device names, not buffer alloc |
| Downgrade kernel | Switch to linux-lts or a 6.17.x-classic kernel with the C binder (`CONFIG_ANDROID_BINDER_IPC=y`) | Restores C binder; avoids Rust driver entirely until fixed upstream |
| Disable rust_binder at build | Set `CONFIG_ANDROID_BINDER_IPC_RUST=n` and enable `CONFIG_ANDROID_BINDER_IPC=y` | Requires rebuilding the kernel package |

**No simpler runtime workaround exists at this time.** The practical mitigation is either kernel downgrade or applying the upstream patch.

---
*Reported by: /home/sin/waydroid-reports/track-d-kernel-regression.md*
