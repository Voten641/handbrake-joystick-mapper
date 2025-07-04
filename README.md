# USB Handbrake to Virtual Xbox 360 Controller Mapper

This Python script allows you to map a USB handbrake (specifically its `ABS_THROTTLE` input) to the X-axis of a virtual Xbox 360 controller. This is particularly useful for racing games that might not natively support your handbrake as a separate axis.

## Features

*   **Device Grabbing:** The script "grabs" the physical handbrake device, making it unavailable to other applications, preventing conflicts.
*   **Virtual Controller Creation:** Creates a virtual Xbox 360 controller using `python-uinput`.
*   **Dynamic Reconnection:** Automatically handles handbrake disconnection and reconnection, ensuring continuous operation.
*   **Systemd Service:** Includes a systemd service file for running the script automatically in the background.

## Requirements

*   Python 3
*   `evdev` library (`python3-evdev`)
*   `python-uinput` library (`python3-uinput`)
*   `sudo` privileges for installation and running the service (due to device access and uinput module).

## Installation

To install and set up the service, you can use the following curl command:

```bash
curl -sSL https://raw.githubusercontent.com/shrek/handbrake-joystick-mapper/main/install.sh | sudo bash
```

This command will:
1. Download the `install.sh` script from the repository.
2. Execute it with `sudo` privileges.

### What the `install.sh` script does:

1.  Installs necessary Python packages (`python3-evdev`, `python3-uinput`).
2.  Copies the `handbrake_to_joystick.py` script to `/usr/local/bin/`.
3.  Creates a systemd service unit file (`handbrake-joystick.service`) in `/etc/systemd/system/`.
4.  Enables and starts the `handbrake-joystick` systemd service.
5.  Creates a udev rule (`99-handbrake.rules`) in `/etc/udev/rules.d/` to ensure proper permissions for the handbrake device.

## Usage

Once installed, the service will start automatically on boot. You can check its status using:

```bash
sudo systemctl status handbrake-joystick
```

To stop the service:

```bash
sudo systemctl stop handbrake-joystick
```

To start the service:

```bash
sudo systemctl start handbrake-joystick
```

To restart the service:

```bash
sudo systemctl restart handbrake-joystick
```

### Manual Run (for testing/debugging)

You can run the script manually (though it's recommended to use the systemd service):

```bash
sudo python3 /usr/local/bin/handbrake_to_joystick.py
```

## Configuration

The script uses the following configuration variables at the top of `handbrake_to_joystick.py`:

*   `HANDBRAKE_DEVICE_PATH`: The path to your handbrake's input event device (e.g., `/dev/input/event24`). **You will likely need to change this.**
    *   To find your handbrake's device path, you can use `cat /proc/bus/input/devices` and look for your handbrake's name, then check the `Handlers` line for `eventX`.
    *   Alternatively, you can use `evtest` (install with `sudo apt install evtest` or `sudo pacman -S evtest`) and interact with your handbrake to see which `/dev/input/eventX` corresponds to it.
*   `ABS_THROTTLE_MIN` and `ABS_THROTTLE_MAX`: These define the expected range of values from your handbrake's `ABS_THROTTLE` input. The script currently assumes 0 to 32767, which is common.

**Important:** After changing `HANDBRAKE_DEVICE_PATH` in `/usr/local/bin/handbrake_to_joystick.py`, you need to restart the service:

```bash
sudo systemctl restart handbrake-joystick
```

## Troubleshooting

*   **Permission Denied:** If you see `Permission denied` errors, ensure you are running the script or the `install.sh` with `sudo`. The `install.sh` script attempts to set up udev rules to grant proper permissions, but sometimes a reboot or `sudo udevadm control --reload-rules && sudo udevadm trigger` might be necessary.
*   **Handbrake Not Found:** Double-check the `HANDBRAKE_DEVICE_PATH` in the script. It's very common for this to change after reboots or if other USB devices are connected/disconnected.

## License

This project is licensed under the MIT License - see the LICENSE file for details (if applicable, otherwise state it's MIT).
