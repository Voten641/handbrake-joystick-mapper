#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

echo "Installing dependencies..."
# Install Python packages using pip
pip install python-evdev uinput

echo "Copying handbrake_to_joystick.py to /usr/local/bin/" 
cp handbrake_to_joystick.py /usr/local/bin/handbrake_to_joystick.py
chmod +x /usr/local/bin/handbrake_to_joystick.py

echo "Creating systemd service file..."
cat <<EOF > /etc/systemd/system/handbrake-joystick.service
[Unit]
Description=USB Handbrake to Virtual Xbox 360 Controller Mapper
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/handbrake_to_joystick.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd daemon, enabling and starting service..."
systemctl daemon-reload
systemctl enable handbrake-joystick
systemctl start handbrake-joystick

echo "Creating udev rule for handbrake device permissions..."
cat <<EOF > /etc/udev/rules.d/99-handbrake.rules
SUBSYSTEM=="input", ATTRS{idVendor}=="1021", ATTRS{idProduct}=="1888", MODE="0666", ENV{ID_INPUT}="1", ENV{ID_INPUT_JOYSTICK}="1"
EOF

echo "
IMPORTANT: You need to replace YOUR_VENDOR_ID and YOUR_PRODUCT_ID in /etc/udev/rules.d/99-handbrake.rules
with the actual Vendor ID and Product ID of your handbrake device.

To find these IDs, plug in your handbrake and run 'lsusb' or 'udevadm monitor --property'.

After updating the udev rule, reload udev rules and trigger:
  sudo udevadm control --reload-rules
  sudo udevadm trigger

Then restart the service:
  sudo systemctl restart handbrake-joystick
"

echo "Installation complete!"
