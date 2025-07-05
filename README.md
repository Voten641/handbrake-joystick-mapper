# Handbrake Joystick Mapper

This is a graphical application that maps a handbrake to a virtual Xbox 360 controller.

## Usage

1.  Download the `handbrake_gui` executable from the [releases page](https://github.com/Voten641/handbrake-joystick-mapper/releases).
2.  Make the file executable: `chmod +x handbrake_gui`
3.  Run the application:
    *   **GUI Mode:** `./handbrake_gui` (Only one instance can run at a time. If an instance is already running in the background, it will be brought to the foreground.)
    *   **Background Mode:** `./handbrake_gui --background`

## Settings

The application includes a settings menu where you can:

*   Adjust the `ABS_THROTTLE_MAX` value to calibrate your handbrake.
*   Enable/disable autostart with the system. When autostart is enabled, the application will run in background mode.
*   Enable/disable "Close to background" mode. When enabled, clicking the close button will hide the window instead of exiting the application.

## Building from Source

If you want to build the application from source, you'll need to have Python and the following dependencies installed:

*   `tkinter`
*   `evdev`
*   `uinput`
*   `pyinstaller`

You can then run the following command to build the application:

```bash
pyinstaller --onefile --windowed --add-binary /usr/lib/python3.13/site-packages/_libsuinput.cpython-313-x86_64-linux-gnu.so:. handbrake_gui.py
```
