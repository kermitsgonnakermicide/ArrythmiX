import simplepyble
import time
import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

if __name__ == "__main__":
    adapters = simplepyble.Adapter.get_adapters()
    adapter = adapters[0]
    print(f"Selected adapter: {adapter.identifier()} [{adapter.address()}]")

    adapter.set_callback_on_scan_start(lambda: print("Scan started."))
    adapter.set_callback_on_scan_stop(lambda: print("Scan complete."))

    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()
    ecg_device = ""
    for i, peripheral in enumerate(peripherals):
        print(f"{i}: {peripheral.identifier()} [{peripheral.address()}]")
        if peripheral.identifier() == "ECG Data":
            print (f"Found ECG Data {peripheral.identifier()}")
            ecg_device = peripheral
    if ecg_device == "":
        print("Could not find an ECG device.")
        exit()

    print(f"Connecting to: {ecg_device.identifier()} [{ecg_device.address()}]")
    ecg_device.connect()

    service_uuid, characteristic_uuid = "0000180d-0000-1000-8000-00805f9b34fb", "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62" #this is stupid

    ecg_device.notify(service_uuid, characteristic_uuid, lambda data: print(data))
    time.sleep(2000)



    ecg_device.disconnect()

