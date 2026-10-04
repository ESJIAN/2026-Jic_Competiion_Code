#!/bin/bash

# WSL Environment Setup Script
# Includes: Basic Tools, ROS 2 Humble (Tsinghua Mirror), Xfce4, TurboVNC, VirtualGL, Python 3.10
# Author: Trae AI

set -e  # Exit immediately if a command exits with a non-zero status.

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup_wsl_env.sh)"
  exit 1
fi

# 1. Basic System Setup
log "Updating system and installing basic dependencies..."
apt update
apt install -y curl wget git vim software-properties-common gnupg2 lsb-release

# Set Locale
log "Setting up Locale..."
apt install -y locales
locale-gen en_US en_US.UTF-8
update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

# 2. Install ROS 2 Humble (Tsinghua Mirror)
log "Installing ROS 2 Humble..."

# Enable Universe
add-apt-repository universe -y

# Add ROS 2 GPG Key (Using keyserver as fallback for stability in China)
log "Adding ROS 2 GPG Key..."
# Try downloading first, fallback to keyserver
if ! curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg; then
    log "Failed to download key from GitHub, trying keyserver..."
    gpg --keyserver keyserver.ubuntu.com --recv-keys F42ED6FBAB17C654
    gpg --export F42ED6FBAB17C654 | tee /usr/share/keyrings/ros-archive-keyring.gpg > /dev/null
fi

# Add Tsinghua Mirror Source
log "Adding Tsinghua ROS 2 Mirror..."
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS 2 Packages
apt update
apt install -y ros-humble-desktop ros-dev-tools

# Environment Setup
if ! grep -q "source /opt/ros/humble/setup.bash" /home/$SUDO_USER/.bashrc; then
    echo "source /opt/ros/humble/setup.bash" >> /home/$SUDO_USER/.bashrc
    
    # Add XDG_RUNTIME_DIR fix
    echo "" >> /home/$SUDO_USER/.bashrc
    echo "# Fix XDG_RUNTIME_DIR warning" >> /home/$SUDO_USER/.bashrc
    echo "export XDG_RUNTIME_DIR=/tmp/runtime-\$USER" >> /home/$SUDO_USER/.bashrc
    echo "mkdir -p \$XDG_RUNTIME_DIR" >> /home/$SUDO_USER/.bashrc
    echo "chmod 700 \$XDG_RUNTIME_DIR" >> /home/$SUDO_USER/.bashrc
    
    log "Added ROS 2 and environment fixes to .bashrc"
fi

# Install rosdepc (Chinese version of rosdep)
log "Installing rosdepc..."
apt install -y python3-pip
pip3 install rosdepc
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    rosdepc init
fi
# Run update as the normal user
su - $SUDO_USER -c "rosdepc update"

# 3. Install Desktop Environment (Xfce4)
log "Installing Xfce4 Desktop Environment..."
apt install -y xfce4 xfce4-goodies

# 4. Install TurboVNC & VirtualGL
log "Installing TurboVNC and VirtualGL..."

# Clean up any old VNC servers if present
apt remove -y tightvncserver tigervnc-standalone-server || true

# Add Repositories
wget -q -O- https://packagecloud.io/dcommander/virtualgl/gpgkey | gpg --dearmor -o /etc/apt/trusted.gpg.d/VirtualGL.gpg --yes
echo "deb https://packagecloud.io/dcommander/virtualgl/any/ any main" | tee /etc/apt/sources.list.d/virtualgl.list

wget -q -O- https://packagecloud.io/dcommander/turbovnc/gpgkey | gpg --dearmor -o /etc/apt/trusted.gpg.d/TurboVNC.gpg --yes
echo "deb https://packagecloud.io/dcommander/turbovnc/any/ any main" | tee /etc/apt/sources.list.d/turbovnc.list

# Install
apt update
apt install -y virtualgl turbovnc

# Configure VNC xstartup for User
VNC_DIR="/home/$SUDO_USER/.vnc"
mkdir -p "$VNC_DIR"
cat > "$VNC_DIR/xstartup" <<EOF
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
[ -x /etc/vnc/xstartup ] && exec /etc/vnc/xstartup
[ -r \$HOME/.Xresources ] && xrdb \$HOME/.Xresources
xsetroot -solid grey
vncconfig -iconic &
startxfce4 &
EOF
chmod +x "$VNC_DIR/xstartup"
chown -R $SUDO_USER:$SUDO_USER "$VNC_DIR"

# Set VNC Password
log "Setting VNC Password..."
echo "12345678" | /opt/TurboVNC/bin/vncpasswd -f > "$VNC_DIR/passwd"
chmod 600 "$VNC_DIR/passwd"
chown $SUDO_USER:$SUDO_USER "$VNC_DIR/passwd"

# 5. Python Environment Setup
log "Configuring Python Environment..."
apt install -y python3.10-venv python3-pip

# 6. Final Cleanup
log "Cleaning up..."
apt autoremove -y

success "WSL Environment Setup Complete!"
echo "--------------------------------------------------------"
echo "To start the VNC Server, run:"
echo "  /opt/TurboVNC/bin/vncserver :0 -geometry 1920x1080 -depth 24"
echo ""
echo "Note: VNC password has been set to: 12345678"
echo "--------------------------------------------------------"
