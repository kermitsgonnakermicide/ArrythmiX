import simplepyble
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from numpy import mean

# === Configuration ===
MAX_POINTS = 200           # Number of points to show in the plot window
PLOT_RANGE = (0, 4)        # Y-axis range for voltage (V), adjust if necessary
SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62"
DEVICE_IDENTIFIER = "ECG Data"
REFERENCE_VOLTAGE = 3.7
# === Setup Data and Plot ===
data = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
fig, ax = plt.subplots()
line, = ax.plot(data)
ax.set_ylim(PLOT_RANGE)
ax.set_title("Live ECG Data")
ax.set_xlabel("Time")
ax.set_ylabel("Voltage (V)")

def notification_callback(received_bytes):
    if received_bytes == b"Leads Off":
        print("Leads Off")
        return
    try:

        adc_value = float(received_bytes.decode('utf-8').strip())
        voltage = (adc_value / 1024) * REFERENCE_VOLTAGE
        print(f"Voltage: {voltage:.2f}V, Mean: {mean(data):.2f}V")
        data.append(voltage)
    except (ValueError, UnicodeDecodeError):
        print(f"Could not decode or convert {received_bytes} to voltage.")

# === Plot Update Function ===
def update(frame):
    line.set_ydata(data)
    return line,

# === Main Execution ===
if __name__ == "__main__":
    adapters = simplepyble.Adapter.get_adapters()

    adapter = adapters[0]
    print(f"Using adapter: {adapter.identifier()} [{adapter.address()}]")
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()

    ecg_device = None
    for peripheral in peripherals:
        if peripheral.identifier() == DEVICE_IDENTIFIER:
            print(f"Found device: {peripheral.identifier()} [{peripheral.address()}]")
            ecg_device = peripheral
            break

    if not ecg_device:
        print(f"Could not find ECG Device")
        exit()

    print("Connecting...")
    ecg_device.connect()
    ecg_device.notify(SERVICE_UUID, CHARACTERISTIC_UUID, notification_callback)

    ani = FuncAnimation(fig, update, interval=50, blit=True)
    try:
        plt.show()
    except KeyboardInterrupt:
        print(data)
        ecg_device.disconnect()
    print("Plot window closed. Disconnecting from device...")
    ecg_device.disconnect()
    print("Disconnected.")
