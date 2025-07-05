# Handbrake Joystick Mapper

This is a graphical application that maps a handbrake to a virtual Xbox 360 controller.

## Usage

1.  Download the `handbrake_gui` executable from the [releases page](https://github.com/Voten641/handbrake-joystick-mapper/releases).
2.  Make the file executable: `chmod +x handbrake_gui`
3.  Run the application: `./handbrake_gui`

## Building from Source

If you want to build the application from source, you'll need to have Python and the following dependencies installed:

*   `tkinter`
*   `evdev`
*   `uinput`
*   `pyinstaller`

You can then run the following command to build the application:

```
pyinstaller --onefile --windowed --add-binary /usr/lib/python3.13/site-packages/_libsuinput.cpython-313-x86_64-linux-gnu.so:. handbrake_gui.py
```
