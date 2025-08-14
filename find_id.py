import hid

for device in hid.enumerate():
    if device['vendor_id'] == 0x0fe7:
        print(device)
