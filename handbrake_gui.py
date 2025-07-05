
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import evdev
import uinput
from evdev import ecodes
import os
import json
import sys
import argparse
import socket
import subprocess

# --- Configuration ---
CONFIG_FILE = os.path.expanduser("~/.handbrake_mapper_config.json")
SINGLE_INSTANCE_PORT = 12345  # Port for single instance communication
ABS_THROTTLE_MAX = 32767
CLOSE_TO_BACKGROUND = False

# --- Global State for Handbrake Logic ---
handbrake_device = None
virtual_device = None
running = False
app_instance = None # Reference to the main application instance

def load_config():
    global ABS_THROTTLE_MAX, CLOSE_TO_BACKGROUND
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            ABS_THROTTLE_MAX = config.get("ABS_THROTTLE_MAX", 32767)
            CLOSE_TO_BACKGROUND = config.get("CLOSE_TO_BACKGROUND", False)

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"ABS_THROTTLE_MAX": ABS_THROTTLE_MAX, "CLOSE_TO_BACKGROUND": CLOSE_TO_BACKGROUND}, f)

def check_single_instance(root):
    global app_instance
    try:
        # Try to connect to an existing instance
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', SINGLE_INSTANCE_PORT))
        s.sendall(b'show')
        s.close()
        sys.exit()  # Exit if another instance is already running
    except ConnectionRefusedError:
        # No other instance running, so this becomes the primary instance
        app_instance = HandbrakeApp(root)
        if CLOSE_TO_BACKGROUND and not args.background: # Only withdraw if not in background mode and close to background is enabled
            root.withdraw()
        threading.Thread(target=start_single_instance_server, args=(root,), daemon=True).start()

def start_single_instance_server(root):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        data = conn.recv(1024)
        if data == b'show':
            root.deiconify()  # Show the window
            root.lift()
            root.attributes('-topmost', True)
            root.attributes('-topmost', False)
        conn.close()

def find_handbrake_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if device.info.vendor == 0x1021 and device.info.product == 0x1888:
            return device
    return None

def cleanup_devices():
    global handbrake_device, virtual_device
    if handbrake_device:
        try:
            handbrake_device.ungrab()
        except OSError:
            pass
        handbrake_device = None
    if virtual_device:
        virtual_device.destroy()
        virtual_device = None

def handbrake_mapping_loop(status_callback=None, value_callback=None):
    global handbrake_device, virtual_device, running
    
    while running:
        try:
            if handbrake_device is None:
                if status_callback: status_callback("Searching for handbrake...")
                handbrake_device = find_handbrake_device()
                if handbrake_device is None:
                    if status_callback: status_callback("Handbrake not found. Retrying...")
                    time.sleep(2)
                    continue

                if status_callback: status_callback(f"Found: {handbrake_device.name}")
                handbrake_device.grab()
                if status_callback: status_callback("Handbrake grabbed.")

                if virtual_device is None:
                    events = (
                        uinput.ABS_X + (-32767, 32767, 0, 0),
                        uinput.ABS_Y + (-32767, 32767, 0, 0),
                        uinput.ABS_RX + (-32767, 32767, 0, 0),
                        uinput.ABS_RY + (-32767, 32767, 0, 0),
                        uinput.ABS_Z + (0, 255, 0, 0),
                        uinput.ABS_RZ + (0, 255, 0, 0),
                        uinput.ABS_HAT0X + (-1, 1, 0, 0),
                        uinput.ABS_HAT0Y + (-1, 1, 0, 0),
                        uinput.BTN_A, uinput.BTN_B, uinput.BTN_X, uinput.BTN_Y,
                        uinput.BTN_TL, uinput.BTN_TR, uinput.BTN_SELECT, uinput.BTN_START,
                        uinput.BTN_MODE, uinput.BTN_THUMBL, uinput.BTN_THUMBR,
                    )
                    virtual_device = uinput.Device(
                        events,
                        name='Xbox 360 Controller',
                        bustype=ecodes.BUS_USB,
                        vendor=0x045E,
                        product=0x028E,
                        version=0x0110
                    )
                    if status_callback: status_callback("Virtual Xbox controller created.")

            for event in handbrake_device.read_loop():
                if not running:
                    break
                if event.type == ecodes.EV_ABS and event.code == ecodes.ABS_THROTTLE:
                    mapped_value = int((event.value / ABS_THROTTLE_MAX) * 32767)
                    if virtual_device:
                        virtual_device.emit(uinput.ABS_X, mapped_value, syn=True)
                    if value_callback: value_callback(event.value)

        except (FileNotFoundError, OSError) as e:
            if status_callback: status_callback(f"Handbrake disconnected: {e}")
            cleanup_devices()
            time.sleep(2)
        except PermissionError:
            if status_callback: status_callback("Permission denied. Run with sudo.")
            running = False
        except Exception as e:
            if status_callback: status_callback(f"An error occurred: {e}")
            cleanup_devices()
            time.sleep(2)

    cleanup_devices()
    if status_callback: status_callback("Stopped.")

# --- GUI ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, app_instance):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x200")

        self.parent = parent
        self.app_instance = app_instance

        self.throttle_max_var = tk.IntVar(value=ABS_THROTTLE_MAX)
        self.autostart_var = tk.BooleanVar(value=self.is_autostart_enabled())
        self.close_to_background_var = tk.BooleanVar(value=CLOSE_TO_BACKGROUND)

        # Store initial values to check for changes
        self._initial_throttle_max = ABS_THROTTLE_MAX
        self._initial_autostart = self.is_autostart_enabled()
        self._initial_close_to_background = CLOSE_TO_BACKGROUND

        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        throttle_frame = ttk.LabelFrame(main_frame, text="Handbrake Settings", padding="10")
        throttle_frame.pack(fill=tk.X, pady=5)

        ttk.Label(throttle_frame, text="Max Throttle Value:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(throttle_frame, textvariable=self.throttle_max_var).pack(side=tk.LEFT, padx=5)

        autostart_frame = ttk.LabelFrame(main_frame, text="Application Settings", padding="10")
        autostart_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(autostart_frame, text="Start with system", variable=self.autostart_var).pack(side=tk.LEFT, padx=5)
        self.close_to_background_checkbox = ttk.Checkbutton(autostart_frame, text="Close to background", variable=self.close_to_background_var)
        self.close_to_background_checkbox.pack(side=tk.LEFT, padx=5)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Automate Setup", command=self.automate_setup).pack(side=tk.LEFT, padx=5)

    def save_settings(self):
        global ABS_THROTTLE_MAX, CLOSE_TO_BACKGROUND
        try:
            new_throttle_max = self.throttle_max_var.get()
            new_autostart = self.autostart_var.get()
            new_close_to_background = self.close_to_background_var.get()

            settings_changed = False
            if new_throttle_max != self._initial_throttle_max:
                ABS_THROTTLE_MAX = new_throttle_max
                self.app_instance.progress.config(maximum=ABS_THROTTLE_MAX)
                settings_changed = True
            
            if new_close_to_background != self._initial_close_to_background:
                CLOSE_TO_BACKGROUND = new_close_to_background
                settings_changed = True

            if new_autostart != self._initial_autostart:
                self.handle_autostart()
                settings_changed = True

            if settings_changed:
                save_config()
                messagebox.showinfo("Settings Saved", "Your settings have been saved.")
            else:
                messagebox.showinfo("No Changes", "No settings were changed.")
            self.destroy()
        except tk.TclError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for the max throttle value.")

    def is_autostart_enabled(self):
        return os.path.exists(f"/etc/systemd/system/handbrake_mapper.service")

    def handle_autostart(self):
        if self.autostart_var.get():
            self.enable_autostart()
        else:
            self.disable_autostart()

    def enable_autostart(self):
        service_content = f"""[Unit]
Description=Handbrake Joystick Mapper Background Service
After=network.target

[Service]
ExecStart=/opt/handbrake_mapper/dist/handbrake_gui --background
Restart=always
User=root

[Install]
WantedBy=multi-user.target
"""
        try:
            with open("/tmp/handbrake_mapper.service", "w") as f:
                f.write(service_content)
            subprocess.run(["sudo", "mv", "/tmp/handbrake_mapper.service", "/etc/systemd/system/handbrake_mapper.service"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "systemctl", "enable", "handbrake_mapper.service"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "systemctl", "start", "handbrake_mapper.service"], check=True, capture_output=True, text=True)
            messagebox.showinfo("Autostart Enabled", "The application will now start automatically with the system.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to enable autostart. Error: {e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to enable autostart: {e}")

    def disable_autostart(self):
        try:
            subprocess.run(["sudo", "systemctl", "stop", "handbrake_mapper.service"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "systemctl", "disable", "handbrake_mapper.service"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "rm", "/etc/systemd/system/handbrake_mapper.service"], check=True, capture_output=True, text=True)
            messagebox.showinfo("Autostart Disabled", "The application will no longer start automatically with the system.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to disable autostart. Error: {e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disable autostart: {e}")

    def automate_setup(self):
        try:
            # Step 2: Add udev rules
            udev_rule_content = 'SUBSYSTEM=="usb", ENV{ID_VENDOR_ID}=="1021", ENV{ID_MODEL_ID}=="1888", RUN+="/bin/sh -c \'echo 1021 1888 > /sys/bus/usb/drivers/usbhid/new_id\'"'
            with open("/tmp/handbrake_mapper_udev.rules", "w") as f:
                f.write(udev_rule_content)
            subprocess.run(["sudo", "mv", "/tmp/handbrake_mapper_udev.rules", "/etc/udev/rules.d/99-handbrake.rules"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "udevadm", "control", "--reload-rules"], check=True, capture_output=True, text=True)
            subprocess.run(["sudo", "udevadm", "trigger"], check=True, capture_output=True, text=True)
            messagebox.showinfo("Udev Rules", "Udev rules applied successfully. You may need to replug your handbrake.")

            # Step 3: Fix permissions
            current_user = os.getlogin()
            subprocess.run(["sudo", "usermod", "-aG", "input", current_user], check=True, capture_output=True, text=True)
            messagebox.showinfo("Permissions", "Permissions fixed successfully. Please log out and log back in for changes to take effect.")

        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to automate setup. Error: {e.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to automate setup: {e}")


class HandbrakeApp:
    def __init__(self, root):
        self.root = root
        root.title("Handbrake Mapper")
        root.geometry("400x250")

        load_config()

        self.status_var = tk.StringVar(value="Ready.")
        self.value_var = tk.IntVar(value=0)

        # Style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#ccc")
        style.configure("TProgressbar", thickness=20)

        # Frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status Label
        status_label = ttk.Label(main_frame, textvariable=self.status_var, wraplength=380)
        status_label.pack(pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=300, mode="determinate", maximum=ABS_THROTTLE_MAX, variable=self.value_var)
        self.progress.pack(pady=10)
        
        # Value Label
        value_label = ttk.Label(main_frame, textvariable=self.value_var)
        value_label.pack()

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(button_frame, text="Start", command=self.start_mapping)
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_mapping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        self.settings_button = ttk.Button(button_frame, text="Settings", command=self.open_settings)
        self.settings_button.pack(side=tk.LEFT, padx=5)

        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def open_settings(self):
        SettingsWindow(self.root, self)

    def update_status(self, message):
        self.root.after(0, self.status_var.set, message)

    def update_value(self, value):
        self.root.after(0, self.value_var.set, value)

    def start_mapping(self):
        global running
        if not running:
            running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress.config(maximum=ABS_THROTTLE_MAX)
            threading.Thread(target=handbrake_mapping_loop, args=(self.update_status, self.update_value), daemon=True).start()

    def stop_mapping(self):
        global running
        if running:
            running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.update_status("Stopping...")
            self.update_value(0)

    def on_closing(self):
        if CLOSE_TO_BACKGROUND:
            self.root.withdraw()  # Hide the window
        else:
            self.stop_mapping()
            self.root.destroy()

if __name__ == "__main__":
    load_config()
    parser = argparse.ArgumentParser(description="Handbrake Joystick Mapper")
    parser.add_argument("--background", action="store_true", help="Run the mapper in background without GUI")
    args = parser.parse_args()

    if args.background:
        running = True
        handbrake_mapping_loop()
    else:
        root = tk.Tk()
        check_single_instance(root)
        root.mainloop()
