- Some overwrites to allow Windows support
- Works for USB-ITN cables
- Requires manual setup using zadig for Windows
- Only tested on Mitutoyo 543-701

# Zadig Setup

1. Options > List All Devices.
2. Select USB-ITN.
3. In the target driver, select libusb0.
4. Replace driver.
5. Done.

Note: After this action the DATA button on the Mitutoyo device will no longer work, you may revert this action by switching back to the original HID driver

## Revert
1. Win + X > Device Manager
2. libusb-win32 devices > USB-ITN
3. Right Click > Update Driver
4. Browse my computer for drivers > Let me pick from a list of available drivers on my computer
5. Select USB Input Device
6. Done

# TO-DO:
- Start/Stop button
- Total number of values