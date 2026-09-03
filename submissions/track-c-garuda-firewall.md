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
