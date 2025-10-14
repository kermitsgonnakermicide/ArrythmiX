import time

import gradio as gr
import simplepyble
import matplotlib.pyplot as plt
from collections import deque
import threading
import numpy as np
from ml.runner import predictor

# === Configuration ===
MAX_POINTS = 200
PLOT_RANGE = (0, 4)
SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62"
DEVICE_IDENTIFIER = "ECG Data"
REFERENCE_VOLTAGE = 3.7
SCAN_DURATION = 5000

# --- Global State ---
data_queue = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
status_text = "Status: Initializing..."
prediction_text = "Prediction: N/A"
bt_thread = None
keep_running = True

def notification_callback(received_bytes):
    """Handles incoming data from the BLE characteristic."""
    global status_text, prediction_text
    if received_bytes == b"Leads Off":
        status_text = "Status: Leads Off"
        return
    try:
        adc_value = float(received_bytes.decode('utf-8').strip())
        voltage = (adc_value / 4095) * REFERENCE_VOLTAGE
        data_queue.append(voltage)

        if len(data_queue) == MAX_POINTS:
            pred = predictor(MAX_POINTS).get_prediction(list(data_queue))
            prediction_text = f"Prediction: {pred}"

    except (ValueError, UnicodeDecodeError):
        status_text = "Status: Error decoding data"

def bluetooth_logic():
    """Scans for and connects to the ECG Bluetooth device."""
    global status_text, keep_running
    status_text = "Status: Searching for Bluetooth adapters..."
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        status_text = "Status: No Bluetooth adapters found."
        return

    adapter = adapters[0]
    status_text = f"Status: Using adapter: {adapter.identifier()}"

    status_text = "Status: Scanning for devices..."
    adapter.scan_for(SCAN_DURATION)
    peripherals = adapter.scan_get_results()

    ecg_device = None
    for p in peripherals:
        if p.identifier() == DEVICE_IDENTIFIER:
            status_text = f"Status: Found device: {p.identifier()}"
            ecg_device = p
            break

    if not ecg_device:
        status_text = "Status: Could not find device."
        return

    try:
        status_text = f"Status: Connecting to {ecg_device.identifier()}..."
        ecg_device.connect()
        status_text = "Status: Connected! Subscribing to notifications..."
        ecg_device.notify(SERVICE_UUID, CHARACTERISTIC_UUID, notification_callback)
        status_text = "Status: Actively receiving ECG data."

        while ecg_device.is_connected() and keep_running:
            pass  # Keep thread alive

    except Exception as e:
        status_text = f"Status: Connection failed: {e}"
    finally:
        if ecg_device and ecg_device.is_connected():
            ecg_device.disconnect()
        status_text = "Status: Disconnected."

def start_scan():
    """Starts the Bluetooth scanning thread."""
    global bt_thread, keep_running, status_text
    print("startedscan")
    keep_running = True
    if bt_thread is None or not bt_thread.is_alive():
        status_text = "Status: Scan initiated..."
        bt_thread = threading.Thread(target=bluetooth_logic, daemon=True)
        bt_thread.start()
    else:
        status_text = "Status: Scan is already running."

def stop_scan():
    """Stops the Bluetooth scanning thread."""
    global keep_running, bt_thread, status_text
    keep_running = False
    if bt_thread and bt_thread.is_alive():
        bt_thread.join(timeout=2) # Wait for thread to finish
    bt_thread = None
    status_text = "Status: Stopped."
    return status_text


def update_plot():
    """Updates the plot with new data."""
    fig, ax = plt.subplots()
    ax.plot(list(data_queue), color='#1f77b4')
    ax.set_ylim(PLOT_RANGE)
    ax.set_title("Arrythmix Demo")
    ax.set_xlabel("Time")
    ax.set_ylabel("Voltage (V)")
    fig.tight_layout()
    return fig, prediction_text, "nothing"

with gr.Blocks() as demo:
    gr.Markdown("# Live ECG Data with Gradio")
    with gr.Row():
        start_button = gr.Button("Start Scan")
        stop_button = gr.Button("Stop Scan")
    
    with gr.Row():
        plot = gr.Plot()
    
    with gr.Row():
        prediction_label = gr.Label(label="Prediction")
        status_label = gr.Label(label="Status")
    start_button.click(start_scan, outputs=None)
    stop_button.click(stop_scan, outputs=[status_label])
    
    demo.load(update_plot, None, [plot, prediction_label, status_label])

if __name__ == "__main__":
    demo.launch()

