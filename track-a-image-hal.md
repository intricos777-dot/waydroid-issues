# Waydroid Missing Audio HAL (vendor.audio-hal-2-0) Investigation

Date: 2026-09-03  
System: Garuda Linux, kernel linux-zen 7.2.2-zen1-1-zen  
Waydroid: 1.6.3-1  
Packages: waydroid-image-gapps installed, initialized with `--system_type VANILLA`

## Findings

### 1. Binary presence
- **vendor.img** (`/usr/share/waydroid-extra/images/vendor.img`) is an ext2 image mounted at `/var/lib/waydroid/rootfs/vendor`.
- `/vendor/bin/hw/android.hardware.audio@2.0-service` is **absent** from vendor.img.
- `/var/lib/waydroid/rootfs/vendor/bin/hw/` does **not exist** on the mounted rootfs.
- vendor.img contains `/bin` with standard Android shell utilities, but no `/vendor/bin/hw` directory.

### 2. Related audio files
- Vendor image and rootfs contain Android audio libraries for **version 4.0** only:
  - `android.hardware.audio@4.0.so`, `android.hardware.audio@4.0-util.so`
  - `android.hardware.audio.common@4.0.so`, `android.hardware.audio.common-util.so`
  - `android.hardware.audio.effect@4.0.so`, `android.hardware.audio.effect@4.0-impl.so`
  - `audio.primary.default.so`, `audio.primary.waydroid.so`, `audio.r_submix.default.so`, `audio.usb.default.so`
- No `android.hardware.audio@2.0-service` binary anywhere.

### 3. Runtime symptom
- Kernel logs (journalctl) repeatedly show:
  ```
  init: Could not start service 'vendor.audio-hal-2-0' ... Cannot find '/vendor/bin/hw/android.hardware.audio@2.0-service'
  ```
- Waydroid reports: Container FROZEN, Vendor type MAINLINE, hardware service "not even started" in some logs.

### 4. Android version context
- Vendor build.prop: `ro.vendor_dlkm.build.version.release=13`, SDK 33.
- Android 13 expects `android.hardware.audio@2.0-service` as part of class `hal`.
- The vendor image is from a recent lineage-waydroid-x86_64 build (dated Apr 28 2026).

### 5. VANILLA vs GAPPS
- `waydroid-image-gapps` package is installed, but the system was initialized with `--system_type VANILLA`.
- The missing binary is in the **vendor** partition, which is shared across VANILLA/GAPPS. Reinitializing with `--system_type GAPPS` would not change the vendor image contents (same `vendor.img` file).
- The Google apps visible in the container suggest the GAPPS system overlay or a custom image was already applied, but that does not fix the vendor partition binary.

## Conclusion
This is **a packaging bug in the upstream Waydroid vendor image** (`lineage_waydroid_x86_64`, build aleasto04282257). The vendor partition is missing the `android.hardware.audio@2.0-service` binary required by the Android 13 init scripts. It is **not expected** behavior for a VANILLA image, nor is it a user error. Both VANILLA and GAPPS image variants using this vendor.img will hit the same failure.

## Recommended Fix

### Immediate workaround (no image rebuild)
1. Stop Waydroid: `sudo systemctl stop waydroid-container` (or `waydroid stop`).
2. Mount vendor.img and create the missing service symlink/script from the existing 4.0 implementation:
   ```
   sudo mkdir -p /mnt/vendor
   sudo mount -o loop /usr/share/waydroid-extra/images/vendor.img /mnt/vendor
   sudo mkdir -p /mnt/vendor/vendor/bin/hw
   sudo ln -sf /vendor/bin/hw/android.hardware.audio@4.0-impl.so /mnt/vendor/vendor/bin/hw/android.hardware.audio@2.0-service
   ```
3. Unmount: `sudo umount /mnt/vendor`.
4. Start Waydroid: `sudo systemctl start waydroid-container`.

   *Caveat:* This is a band-aid. Version mismatch (2.0 vs 4.0) may cause functional issues depending on the AIDL interface version the host expects.

### Proper fix
1. **File an upstream bug** against the Waydroid image build for `lineage_waydroid_x86_64` reporting that `android.hardware.audio@2.0-service` is missing from vendor.img for SDK 33 / Android 13 images.
2. Update to a newer `waydroid-image-*` package once upstream publishes a fixed vendor.img.
3. Alternatively, rebuild vendor.img including `android.hardware.audio@2.0-service` (or symlink from the 4.0 impl) via the image generation scripts.

### Avoid reinitializing
Reinitializing with `--system_type GAPPS` will **not** fix this because it uses the same `vendor.img`. Only replacing or patching the vendor image will resolve the missing HAL.
