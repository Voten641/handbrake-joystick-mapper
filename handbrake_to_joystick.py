import evdev
import uinput
import time
from evdev import ecodes

# Configuration
HANDBRAKE_DEVICE_PATH = '/dev/input/event24'
ABS_THROTTLE_MIN = 0
ABS_THROTTLE_MAX = 32767

# Define the virtual Xbox 360 controller device
events = (
    # Left Stick
    uinput.ABS_X + (-32767, 32767, 0, 0),
    uinput.ABS_Y + (-32767, 32767, 0, 0),
    # Right Stick
    uinput.ABS_RX + (-32767, 32767, 0, 0),
    uinput.ABS_RY + (-32767, 32767, 0, 0),
    # Triggers (often 0-255 or 0-1023, using 0-255 for simplicity)
    uinput.ABS_Z + (0, 255, 0, 0), # Left Trigger
    uinput.ABS_RZ + (0, 255, 0, 0), # Right Trigger
    # D-Pad (Hat Switch)
    uinput.ABS_HAT0X + (-1, 1, 0, 0),
    uinput.ABS_HAT0Y + (-1, 1, 0, 0),
    # Buttons
    uinput.BTN_A,
    uinput.BTN_B,
    uinput.BTN_X,
    uinput.BTN_Y,
    uinput.BTN_TL, # Left Bumper
    uinput.BTN_TR, # Right Bumper
    uinput.BTN_SELECT, # Back button
    uinput.BTN_START, # Start button
    uinput.BTN_MODE, # Xbox/Guide button
    uinput.BTN_THUMBL, # Left Stick Click
    uinput.BTN_THUMBR, # Right Stick Click
)

handbrake_device = None  # Initialize to None
virtual_device = None  # Initialize to None

try:
    while True:
        try:
            if handbrake_device is None:
                # Try to find the handbrake device
                handbrake_device = evdev.InputDevice(HANDBRAKE_DEVICE_PATH)
                print(f"Monitoring handbrake: {handbrake_device.name} ({handbrake_device.path})")

                # Grab the handbrake device to hide it from other applications
                handbrake_device.grab()
                print(f"Handbrake device grabbed. It is now hidden from other applications.")

                # Create the virtual device ONLY when handbrake is found
                if virtual_device is None:
                    virtual_device = uinput.Device(
                        events,
                        name='Xbox 360 Controller',
                        bustype=ecodes.BUS_USB,
                        vendor=0x045E,
                        product=0x028E,
                        version=0x0110
                    )
                    print(f"Virtual Xbox 360 Controller created.")

            # Main loop to read handbrake input and send to virtual joystick
            for event in handbrake_device.read_loop():
                if virtual_device: # Ensure virtual device exists before emitting
                    if event.type == evdev.ecodes.EV_ABS and event.code == evdev.ecodes.ABS_THROTTLE:
                        # Map the handbrake value (0 to 32767) to Xbox ABS_X (-32767 to 32767)
                        mapped_value = int((event.value / ABS_THROTTLE_MAX) * 32767)
                        virtual_device.emit(uinput.ABS_X, mapped_value, syn=True)
                        # print(f"Handbrake (ABS_THROTTLE): {event.value} -> Xbox ABS_X: {mapped_value}")

        except (FileNotFoundError, OSError) as e:
            if handbrake_device:
                try:
                    handbrake_device.ungrab()
                    print("Handbrake device ungrabbed due to disconnection.")
                except OSError as ungrab_e:
                    print(f"Error ungrabbing device: {ungrab_e}")
                finally:
                    handbrake_device = None
            if virtual_device: # Close virtual device if handbrake disconnected
                try:
                    virtual_device.close()
                    print("Virtual device closed due to handbrake disconnection.")
                except Exception as close_e:
                    print(f"Error closing virtual device: {close_e}")
                finally:
                    virtual_device = None
            print(f"Handbrake device not found or disconnected: {e}. Retrying in 2 seconds...")
            time.sleep(2)
        except PermissionError:
            print("Error: Permission denied. You might need to run this script with sudo or set up udev rules. Exiting.")
            break # Exit if permission error occurs
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Retrying in 2 seconds...")
            if handbrake_device:
                try:
                    handbrake_device.ungrab()
                except OSError as ungrab_e:
                    print(f"Error ungrabbing device: {ungrab_e}")
                finally:
                    handbrake_device = None
            if virtual_device: # Close virtual device on other errors too
                try:
                    virtual_device.close()
                except Exception as close_e:
                    print(f"Error closing virtual device: {close_e}")
                finally:
                    virtual_device = None
            time.sleep(2)

finally:
    # Ensure the device is ungrabbed if the script exits
    if handbrake_device:
        try:
            handbrake_device.ungrab()
            print("Handbrake device ungrabbed.")
        except OSError as e:
            print(f"Error ungrabbing device: {e}")
    if virtual_device:
        virtual_device.close()
        print("Virtual device closed.")