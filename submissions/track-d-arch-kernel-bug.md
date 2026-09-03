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
