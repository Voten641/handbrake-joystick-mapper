
import tkinter as tk
from tkinter import ttk
import threading
import time
import evdev
import uinput
from evdev import ecodes

# --- Configuration ---
ABS_THROTTLE_MAX = 32767

# --- Handbrake Logic ---
handbrake_device = None
virtual_device = None
running = False
thread = None

def find_handbrake_device():
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        if device.info.vendor == 0x1021 and device.info.product == 0x1888:
            return device
    return None

def handbrake_thread(status_callback, value_callback):
    global handbrake_device, virtual_device, running
    
    while running:
        try:
            if handbrake_device is None:
                status_callback("Searching for handbrake...")
                handbrake_device = find_handbrake_device()
                if handbrake_device is None:
                    status_callback("Handbrake not found. Retrying...")
                    time.sleep(2)
                    continue

                status_callback(f"Found: {handbrake_device.name}")
                handbrake_device.grab()
                status_callback("Handbrake grabbed.")

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
                    status_callback("Virtual Xbox controller created.")

            for event in handbrake_device.read_loop():
                if not running:
                    break
                if event.type == ecodes.EV_ABS and event.code == ecodes.ABS_THROTTLE:
                    mapped_value = int((event.value / ABS_THROTTLE_MAX) * 32767)
                    if virtual_device:
                        virtual_device.emit(uinput.ABS_X, mapped_value, syn=True)
                    value_callback(event.value)

        except (FileNotFoundError, OSError) as e:
            status_callback(f"Handbrake disconnected: {e}")
            cleanup_devices()
            time.sleep(2)
        except PermissionError:
            status_callback("Permission denied. Run with sudo.")
            running = False
        except Exception as e:
            status_callback(f"An error occurred: {e}")
            cleanup_devices()
            time.sleep(2)

    cleanup_devices()
    status_callback("Stopped.")

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

# --- GUI ---
class HandbrakeApp:
    def __init__(self, root):
        self.root = root
        root.title("Handbrake Mapper")
        root.geometry("400x200")

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

        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def update_status(self, message):
        self.root.after(0, self.status_var.set, message)

    def update_value(self, value):
        self.root.after(0, self.value_var.set, value)

    def start_mapping(self):
        global running, thread
        if not running:
            running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            thread = threading.Thread(target=handbrake_thread, args=(self.update_status, self.update_value))
            thread.daemon = True
            thread.start()

    def stop_mapping(self):
        global running
        if running:
            running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.update_status("Stopping...")
            self.update_value(0)


    def on_closing(self):
        self.stop_mapping()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = HandbrakeApp(root)
    root.mainloop()
