from pytuyo import Pytuyo
import usb.core
import platform
import logging
import sys

VENDOR_ID = 0x0FE7
PRODUCT_ID = 0x4001

# Suppress pytuyo logging messages
logging.getLogger("pytuyo").setLevel(logging.CRITICAL)

# Patch the setup method if on Windows
def windows_patch(self):
    self._usb_dev.reset()
    self._usb_dev.set_configuration(1)
    c = self._usb_dev.get_active_configuration()
    self._epin = c.interfaces()[0].endpoints()[0]

    bmRequestType = 0x40
    self._usb_dev.ctrl_transfer(bmRequestType, 0x01, 0xA5A5, 0)

    bmRequestType = 0xC0
    resp = self._usb_dev.ctrl_transfer(bmRequestType, 0x02, 0, 0, 1)

def find_device():
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        print("Mitutoyo device not found.")
        sys.exit(1)
    return device

def vcp_test(device):
    try:
        device.ctrl_transfer(0xC0, 0x02, 0, 0, 1)  # Probe VCP
    except NotImplementedError as e:
        print("Device likely still using HID driver — use Zadig to install libusb-win32.")
        print("Details:", e)
        sys.exit(1)
    except usb.core.USBError as e:
        print("USB communication failed.")
        print("Details:", e)
        sys.exit(1)

# Read
def read():
    d = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    device = Pytuyo(d)
    value = device.get_reading(timeout=2)
    return value

def main():
    if platform.system() == "Windows":
        Pytuyo.setup = windows_patch
    device = find_device()
    vcp_test(device)
    print(read())

if __name__ == "__main__":
    main()