# ProtonVPN Split Tunnel — Keep VPS Access While VPN Is On

ProtonVPN sometimes routes ALL traffic through the tunnel, including your SSH
connection to 187.77.208.156. Split tunneling tells ProtonVPN to exclude the
VPS IP from the tunnel so it always goes direct.

---

## Option A — Exclude the VPS IP (Recommended)

This is the cleanest fix. The VPS IP bypasses the VPN entirely.

### Windows App (ProtonVPN v3+)
1. Open ProtonVPN → **Settings** → **Split Tunneling**
2. Toggle **Split Tunneling** ON
3. Choose **"Exclude selected IPs and apps"**
4. Click **Add IP** and enter: `187.77.208.156`
5. Save — reconnect VPN

Your SSH to `187.77.208.156:2222` will now always go direct, VPN or not.

### Linux CLI (protonvpn-cli)
```bash
protonvpn-cli s --split-tunneling 1
protonvpn-cli s --split-tunnel-ip add 187.77.208.156
protonvpn-cli reconnect
```

---

## Option B — Custom DNS / Route (Advanced)

If split tunneling is unavailable on your plan, add a persistent static route
so the VPS IP always goes through your real gateway, not the VPN tunnel.

### Windows (run as Administrator)
```cmd
# Find your real gateway first:
ipconfig

# Add static route (replace 192.168.1.1 with your actual gateway):
route add 187.77.208.156 mask 255.255.255.255 192.168.1.1 -p
```
The `-p` flag makes it persistent across reboots.

To remove it later:
```cmd
route delete 187.77.208.156
```

### Linux
```bash
# Find your real gateway:
ip route | grep default

# Add persistent route (replace 192.168.1.1 with your gateway):
sudo ip route add 187.77.208.156 via 192.168.1.1

# Make it persistent (add to /etc/network/interfaces or netplan):
# Ubuntu/Debian with netplan:
# under your interface in /etc/netplan/01-netcfg.yaml:
#   routes:
#     - to: 187.77.208.156/32
#       via: 192.168.1.1
```

---

## Option C — ProtonVPN Kill Switch Interaction

If you're using ProtonVPN's **Kill Switch**, it blocks ALL non-VPN traffic when
the VPN drops. This will kill your SSH session on disconnect.

Fix: **Don't use Kill Switch** while doing VPS work, or use **App Kill Switch**
(blocks only specific apps) instead of the system-wide one.

Windows: Settings → Kill Switch → switch from "Permanent" to "App" mode.

---

## Verifying It Works

After configuring, test with VPN connected:
```bash
# Should return 187.77.208.156 (your real connection to VPS)
ssh -p 2222 -v root@187.77.208.156 "echo 'VPN bypass working'"

# Check what IP the VPS sees your connection from:
ssh -p 2222 root@187.77.208.156 "echo \$SSH_CLIENT"
# First field = your connecting IP
```

---

## Your VPS SSH Config Reference

```
Host hostinger-vps
    HostName 187.77.208.156
    User root
    Port 2222
    IdentityFile ~/.ssh/id_ed25519
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

`ServerAliveInterval 60` + `ServerAliveCountMax 3` keeps the connection alive
and detects drops quickly — prevents hanging terminals when VPN switches.
