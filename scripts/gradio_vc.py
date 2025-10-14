import simplepyble
import threading
import time
from collections import deque
import matplotlib.pyplot as plt
import numpy as np
import gradio as gr
import random
from numpy import mean

# === Configuration ===
MAX_POINTS = 200
PLOT_RANGE = (0, 4)
SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62"
DEVICE_IDENTIFIER = "ECG Data"
REFERENCE_VOLTAGE = 3.7

# === Data and state ===
data = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
device = None
stop_flag = False
using_fake_data = False


# === BLE Functions ===
def scan_and_connect():
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapters found.")
        return None

    adapter = adapters[0]
    print(f"Using adapter: {adapter.identifier()} [{adapter.address()}]")
    print("Scanning for devices (5 seconds)...")
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()

    found_device = None
    for p in peripherals:
        print(f"Found: {p.identifier()} [{p.address()}]")
        if p.identifier() == DEVICE_IDENTIFIER:
            found_device = p
            break

    if not found_device:
        print(f"Could not find '{DEVICE_IDENTIFIER}'.")
        return None

    print(f"Connecting to {found_device.identifier()}...")
    found_device.connect()
    found_device.notify(SERVICE_UUID, CHARACTERISTIC_UUID, notification_callback)
    print("Connected successfully.")
    return found_device


def notification_callback(received_bytes):
    if received_bytes == b"Leads Off":
        print("Leads Off")
        return
    try:
        adc_value = float(received_bytes.decode("utf-8").strip())
        voltage = (adc_value / 1024) * REFERENCE_VOLTAGE
        data.append(voltage)
    except Exception:
        pass


# === Background Data Threads ===
def fake_data_feed():
    global stop_flag
    while not stop_flag:
        data.append(2 + 1.5 * (random.random() - 0.5))
        time.sleep(0.05)


def real_data_feed():
    global stop_flag
    while not stop_flag:
        time.sleep(0.001)


# === Plotting ===
def plot_ecg():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(list(range(len(data))), list(data), color="red")
    ax.set_ylim(PLOT_RANGE)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(f"Live ECG Signal (mean={mean(data):.2f} V)")
    ax.grid(True)
    return fig


# === Gradio Live Update Function ===
def stream_plot():
    while True:
        yield plot_ecg()
        time.sleep(0.3)


# === Prelaunch Console Logic ===
if __name__ == "__main__":
    choice = input("Skip device scan? (y/n): ").strip().lower()

    if choice == "y":
        using_fake_data = True
        print("Using simulated ECG data.")
        threading.Thread(target=fake_data_feed, daemon=True).start()
    else:
        device = scan_and_connect()
        if device is None:
            print("Falling back to simulated data.")
            using_fake_data = True
            threading.Thread(target=fake_data_feed, daemon=True).start()
        else:
            threading.Thread(target=real_data_feed, daemon=True).start()

    # === Gradio UI ===
    with gr.Blocks() as ui:
        gr.Markdown("## ArrythmiX ECG Monitor")
        gr.Markdown("Displaying ECG signal in real time. Close the window or press Stop to end.")

        graph = gr.Plot(label="")

        ui.load(stream_plot, None, graph, stream_every=0.01)

    ui.launch()
