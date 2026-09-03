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
