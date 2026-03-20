#!/usr/bin/env bash
set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
VPS_HOST="187.77.208.156"
VPS_PORT="2222"
VPS_USER="root"
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_ALIAS="hostinger-vps"
SSH_CONFIG="$HOME/.ssh/config"
TOTAL_STEPS=6

# ── Colors ──────────────────────────────────────────────────────────────────
if command -v tput &>/dev/null && tput colors &>/dev/null 2>&1; then
  GREEN=$(tput setaf 2)
  RED=$(tput setaf 1)
  CYAN=$(tput setaf 6)
  YELLOW=$(tput setaf 3)
  BOLD=$(tput bold)
  RESET=$(tput sgr0)
else
  GREEN=''; RED=''; CYAN=''; YELLOW=''; BOLD=''; RESET=''
fi

# ── Helpers ──────────────────────────────────────────────────────────────────
ok()   { printf "${GREEN}✔${RESET} %s\n" "$*"; }
fail() { printf "${RED}✖${RESET} %s\n" "$*" >&2; }
info() { printf "${CYAN}ℹ${RESET} %s\n" "$*"; }
warn() { printf "${YELLOW}⚠${RESET} %s\n" "$*"; }
step() { printf "\n${BOLD}[%s/%s] %s${RESET}\n" "$1" "$TOTAL_STEPS" "$2"; }

# ── Banner ───────────────────────────────────────────────────────────────────
printf "\n${BOLD}════════════════════════════════════════════════${RESET}\n"
printf "${BOLD}  universal369 — Linux Environment Bootstrap${RESET}\n"
printf "${BOLD}════════════════════════════════════════════════${RESET}\n"
printf "  VPS: %s:%s (user: %s)\n" "$VPS_HOST" "$VPS_PORT" "$VPS_USER"
printf "  SSH alias: %s\n\n" "$SSH_ALIAS"

# ────────────────────────────────────────────────────────────────────────────
step 1 "Install openssh-client"
if command -v ssh &>/dev/null; then
  ok "ssh already installed ($(command -v ssh))"
else
  info "ssh not found — installing openssh-client..."
  apt-get install -y openssh-client
  ok "openssh-client installed"
fi

# ────────────────────────────────────────────────────────────────────────────
step 2 "Generate SSH key"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [[ -f "$SSH_KEY" ]]; then
  ok "SSH key already exists at $SSH_KEY"
else
  info "Generating new ed25519 key..."
  ssh-keygen -t ed25519 -C "universal369-deploy" -f "$SSH_KEY" -N ""
  ok "SSH key created"
fi

info "Key fingerprint:"
ssh-keygen -lf "$SSH_KEY"

# ────────────────────────────────────────────────────────────────────────────
step 3 "Your public key (copy this into hPanel)"
printf "\n${BOLD}${YELLOW}┌─────────────────────────────────────────────────────┐${RESET}\n"
printf "${BOLD}${YELLOW}│  COPY THE LINE BELOW → paste into hPanel SSH Keys  │${RESET}\n"
printf "${BOLD}${YELLOW}└─────────────────────────────────────────────────────┘${RESET}\n\n"
cat "${SSH_KEY}.pub"
printf "\n"
ok "Public key displayed above"

# ────────────────────────────────────────────────────────────────────────────
step 4 "Write SSH config (~/.ssh/config)"
if grep -q "Host ${SSH_ALIAS}" "$SSH_CONFIG" 2>/dev/null; then
  ok "hostinger-vps alias already in $SSH_CONFIG"
else
  # Ensure file exists and has a newline before appending
  if [[ -f "$SSH_CONFIG" ]]; then
    # Add blank line separator if file doesn't end with newline
    [[ -z "$(tail -c1 "$SSH_CONFIG")" ]] || printf "\n" >> "$SSH_CONFIG"
  fi

  cat >> "$SSH_CONFIG" <<EOF

Host ${SSH_ALIAS}
    HostName ${VPS_HOST}
    Port ${VPS_PORT}
    User ${VPS_USER}
    IdentityFile ${SSH_KEY}
    StrictHostKeyChecking accept-new
EOF

  ok "hostinger-vps alias added to $SSH_CONFIG"
fi

chmod 600 "$SSH_CONFIG"
ok "Permissions set: ~/.ssh=700, config=600"

# ────────────────────────────────────────────────────────────────────────────
step 5 "Test SSH connectivity"
info "Connecting to ${SSH_ALIAS} (timeout 10s)..."
if ssh -o ConnectTimeout=10 -o BatchMode=yes "$SSH_ALIAS" "echo connected" 2>/dev/null; then
  ok "SSH connection successful!"
else
  warn "SSH connection failed — this may be expected if the public key"
  warn "hasn't been added to hPanel yet, or if this IP is network-blocked."
  warn "Continuing anyway..."
fi

# ────────────────────────────────────────────────────────────────────────────
step 6 "Next steps"
printf "\n${BOLD}What to do now:${RESET}\n\n"
printf "  ${CYAN}1.${RESET} Copy the public key printed in step 3 above\n"
printf "  ${CYAN}2.${RESET} Paste it into hPanel → VPS → SSH Keys\n"
printf "     (hpanel.hostinger.com → your VPS → SSH tab)\n\n"
printf "  ${CYAN}3.${RESET} Test the connection:\n"
printf "     ${BOLD}ssh hostinger-vps${RESET}\n\n"
printf "  ${CYAN}4.${RESET} Once connected, deploy the site:\n"
printf "     ${BOLD}cd /home/user/universal369${RESET}\n"
printf "     ${BOLD}scp -P 2222 index.html cosmic-energy-enhanced.mp4 \\\n"
printf "       root@187.77.208.156:/home/universal369.com/public_html/${RESET}\n\n"
printf "  ${CYAN}5.${RESET} Verify the site is live:\n"
printf "     ${BOLD}curl -s -o /dev/null -w \"%%{http_code}\" https://universal369.com${RESET}\n\n"

printf "${BOLD}${GREEN}════ Bootstrap complete ════${RESET}\n\n"
