from pytuyo import Pytuyo
import usb.core
import platform
import logging
import sys
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt5.QtWidgets import (
    QInputDialog, QMessageBox,
    QPushButton, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel  # <-- added
)
import time
import csv
from datetime import datetime
import numpy as np
from pathlib import Path

VENDOR_ID = 0x0FE7
PRODUCT_ID = 0x4001

# Suppress pytuyo logging messages
logging.getLogger("pytuyo").setLevel(logging.CRITICAL)

# Windows USB patch
def windows_patch(self):
    self._usb_dev.reset()
    self._usb_dev.set_configuration(1)
    c = self._usb_dev.get_active_configuration()
    self._epin = c.interfaces()[0].endpoints()[0]
    bmRequestType = 0x40
    self._usb_dev.ctrl_transfer(bmRequestType, 0x01, 0xA5A5, 0)
    bmRequestType = 0xC0
    self._usb_dev.ctrl_transfer(bmRequestType, 0x02, 0, 0, 1)

# USB helpers
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
        print("Device likely still using HID driver — use Zadig to install WinUSB.")
        print("Details:", e)
        sys.exit(1)
    except usb.core.USBError as e:
        print("USB communication failed.")
        print("Details:", e)
        sys.exit(1)

# Qt helpers
def prompt_interval_qt(parent=None, default=0.05):
    """Ask for update interval (seconds) via Qt dialog; re-prompt until valid."""
    while True:
        value, ok = QInputDialog.getDouble(
            parent, "Update Interval",
            "Enter update interval (seconds):",
            decimals=3, value=default, min=0.001, max=3600.0
        )
        if ok and value > 0:
            return float(value)
        choice = QMessageBox.question(
            parent, "Invalid or Cancelled",
            "No valid interval provided. Try again?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        if choice == QMessageBox.No:
            sys.exit(0)

def main():
    # Apply patch for Windows
    if platform.system() == "Windows":
        Pytuyo.setup = windows_patch

    # Init Qt
    app = QtWidgets.QApplication(sys.argv)

    # Ask user for interval (seconds)
    INTERVAL_S = prompt_interval_qt(default=1)

    # Connect once
    device = find_device()
    vcp_test(device)
    mitutoyo = Pytuyo(device)

    # Prepare CSV with header
    DATA_DIR = Path("data")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get time for filename
    now = datetime.now()
    filename_base = f"Mitutoyo_Measurements_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S')}"

    # Ensure no overwrite by adding _2, _3... if needed
    csv_path = DATA_DIR / f"{filename_base}.csv"
    counter = 2
    while csv_path.exists():
        csv_path = DATA_DIR / f"{filename_base}_{counter}.csv"
        counter += 1

    # Prepare CSV with header
    with open(csv_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "value_mm"])

    # UI
    root = QWidget()
    root.setWindowTitle("Real-Time Measurement")

    # Layout for the main window
    pg_win = pg.GraphicsLayoutWidget(show=True)
    plot = pg_win.addPlot(title="Length vs Time")
    plot.setLabel('bottom', 'Time', 's')
    plot.setLabel('left', 'Length', 'mm')
    curve = plot.plot(pen='y')

    btn_start = QPushButton("Start")
    btn_stop  = QPushButton("Stop")
    btn_stop.setEnabled(False)

    for b in (btn_start, btn_stop):
        b.setMinimumHeight(72)
        b.setStyleSheet("font-size: 20px;")
        b.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    buttons = QHBoxLayout()
    buttons.setContentsMargins(0, 0, 0, 0)
    buttons.setSpacing(12)
    buttons.addWidget(btn_start, 1)
    buttons.addWidget(btn_stop, 1)

    layout = QVBoxLayout(root)
    layout.setContentsMargins(12, 12, 12, 12)
    layout.setSpacing(12)
    layout.addWidget(pg_win)
    layout.addLayout(buttons)
    layout.setStretch(0, 1)
    layout.setStretch(1, 0)

    # --- Added: readings counter label (inserted without changing existing widgets) ---
    stats = QHBoxLayout()
    stats.setContentsMargins(0, 0, 0, 0)
    stats.setSpacing(0)
    label_count = QLabel("Readings: 0")
    label_count.setStyleSheet("font-size: 18px; padding: 4px 0;")
    stats.addWidget(label_count)
    stats.addStretch(1)
    layout.insertLayout(1, stats)  # place between plot and buttons
    # --- end added ---

    root.resize(1000, 680)
    root.show()

    # Data buffers
    data_x, data_y = [], []
    start_time = time.time()
    is_running = False
    readings_count = 0  # <-- added

    def append_csv(val):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        with open(csv_path, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ts, val])

    def update():
        nonlocal readings_count  # <-- added
        if not is_running:
            return
        t = time.time() - start_time
        try:
            val = mitutoyo.get_reading(timeout=2)
            if val is not None:
                data_x.append(t)
                data_y.append(val)
                curve.setData(data_x, data_y)
                append_csv(val)
                readings_count += 1                           # <-- added
                label_count.setText(f"Readings: {readings_count}")  # <-- added
        except usb.core.USBError as e:
            print("Read error:", e)

    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(int(INTERVAL_S * 1000))  # ms

    # Button handlers
    def on_start():
        nonlocal is_running
        is_running = True
        btn_start.setEnabled(False)
        btn_stop.setEnabled(True)

    def on_stop():
        nonlocal is_running
        # Disconnect curve
        t = time.time() - start_time
        data_x.append(t)
        data_y.append(np.nan)
        curve.setData(data_x, data_y)

        is_running = False
        btn_start.setEnabled(True)
        btn_stop.setEnabled(False)

    btn_start.clicked.connect(on_start)
    btn_stop.clicked.connect(on_stop)

    # Do NOT autostart

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
