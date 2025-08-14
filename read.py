from pytuyo import Pytuyo
import usb.core
import platform
import logging
import usb.util
import sys

VENDOR_ID = 0x0FE7
PRODUCT_ID = 0x4001

# Suppress pytuyo logging messages
logging.getLogger("pytuyo").setLevel(logging.CRITICAL)

# Patch the setup method if on Windows
if platform.system() == "Windows":
    def patched_setup(self):
        self._usb_dev.reset()
        self._usb_dev.set_configuration(1)
        c = self._usb_dev.get_active_configuration()
        self._epin = c.interfaces()[0].endpoints()[0]

        bmRequestType = 0x40
        self._usb_dev.ctrl_transfer(bmRequestType, 0x01, 0xA5A5, 0)

        bmRequestType = 0xC0
        resp = self._usb_dev.ctrl_transfer(bmRequestType, 0x02, 0, 0, 1)
    
    Pytuyo.setup = patched_setup

device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

if device is None:
    print("Mitutoyo device not found.")
    sys.exit(1)

try:
    device.set_configuration()
    # Attempt harmless control transfer
    device.ctrl_transfer(0xC0, 0x02, 0, 0, 1)  # Just probe VCP response
except usb.core.USBError as e:
    print("Failed to communicate with device.")
    print("This likely means it's still using the default HID driver.")
    print("Use Zadig to install the WinUSB driver for this device.")
    print(f"Error details: {e}")
    sys.exit(1)

# Read
d = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
device = Pytuyo(d)
value = device.get_reading(timeout=2)
print(value)
