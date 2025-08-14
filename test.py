import usb.core
d = usb.core.find(idVendor=0x0fe7, idProduct=0x4001)
print("Device found" if d else "Device not found")
