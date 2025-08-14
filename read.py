from pytuyo import Pytuyo
import usb.core
import platform
import logging
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import QInputDialog, QMessageBox
import time
import csv
from datetime import datetime

VENDOR_ID = 0x0FE7
PRODUCT_ID = 0x4001
INTERVAL_S = 0.05

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
    self._usb_dev.ctrl_transfer(bmRequestType, 0x02, 0, 0, 1)

# Find USB device
def find_device():
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    if device is None:
        print("Mitutoyo device not found.")
        sys.exit(1)
    return device

# Check if device is ready
def vcp_test(device):
    try:
        device.ctrl_transfer(0xC0, 0x02, 0, 0, 1)  # Probe VCP
    except NotImplementedError as e:
        print("Device likely still using HID driver — use Zadig to install WinUSB.")
        print("Details:", e)
        sys.exit(1)
    except usb.core.USBError as e:
        print("USB communication failed.")
        print("Details:", e)
        sys.exit(1)

def prompt_interval_qt(parent=None, default=0.05):
    """
    Show a Qt dialog to ask for the update interval in seconds.
    Keeps prompting until the user enters a valid number (>0) or confirms exit.
    Returns a float (seconds).
    """
    while True:
        value, ok = QInputDialog.getDouble(
            parent,
            "Update Interval",
            "Enter update interval (seconds):",
            decimals=3,
            value=default,
            min=0.001,   # prevent zero / negative
            max=3600.0,  # up to 1 hour if you like
        )
        if ok and value > 0:
            return float(value)

        # If user pressed cancel or invalid value, confirm exit or retry
        choice = QMessageBox.question(
            parent,
            "Invalid or Cancelled",
            "No valid interval provided. Do you want to try again?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if choice == QMessageBox.No:
            sys.exit(0)

def main():
    global mitutoyo, data_x, data_y, start_time

    # Apply patch for Windows
    if platform.system() == "Windows":
        Pytuyo.setup = windows_patch

    # Connect once
    device = find_device()
    vcp_test(device)
    mitutoyo = Pytuyo(device)

    # Init PyQtGraph
    app = QtWidgets.QApplication(sys.argv)
    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Measurement")
    plot = win.addPlot(title="Length vs Time")
    plot.setLabel('bottom', 'Time', 's')
    plot.setLabel('left', 'Length', 'mm')
    curve = plot.plot(pen='y')

    # Data buffers
    data_x = []
    data_y = []
    start_time = time.time()

    # Update function
    def update():
        t = time.time() - start_time
        try:
            val = mitutoyo.get_reading(timeout=2)  # direct read from device
            if val is not None:
                data_x.append(t)
                data_y.append(val)
                curve.setData(data_x, data_y)
        except usb.core.USBError as e:
            print("Read error:", e)

    INTERVAL_S = prompt_interval_qt(default=0.05)

    # Timer for updates
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(int(INTERVAL_S * 1000))  # Convert to milliseconds

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
