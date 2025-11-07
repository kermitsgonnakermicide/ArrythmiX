# gradio_ecg_infer.py
import threading
import time
from collections import deque
import matplotlib.pyplot as plt
import numpy as np
import gradio as gr
import simplepyble
from ml.runner import predictor  # your predictor class
import random

# === Configuration ===
MAX_POINTS = 200                 # points shown on plot (sliding window)
PLOT_RANGE = (0, 4)              # y-axis limits (V)
SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62"
DEVICE_IDENTIFIER = "ECG Data"
REFERENCE_VOLTAGE = 3.7
SCAN_DURATION = 5000             # ms for simplepyble.scan_for
INFERENCE_TRIGGER_COUNT = 40     # run inference every N new samples
INFERENCE_WINDOW_SIZE = 171      # samples to send to predictor (it will resample if needed)
PLOT_UPDATE_INTERVAL = 0.3       # seconds between UI plot updates

# === Shared state / concurrency primitives ===
plot_lock = threading.Lock()
inference_lock = threading.Lock()
stop_event = threading.Event()

plot_buffer = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
inference_buffer = deque(maxlen=INFERENCE_WINDOW_SIZE)

# Predictor (loads model inside its __init__)
predictor_obj = predictor(INFERENCE_WINDOW_SIZE)

# last prediction (protected by inference_lock)
_last_prediction = "N/A"

# Device handle
ecg_device = None


# ---------------- BLE / Simulated Feed ----------------
def ble_notification_callback(received_bytes):
    """Callback from simplepyble notifications."""
    global _last_prediction
    if stop_event.is_set():
        return
    try:
        if received_bytes == b"Leads Off":
            # optional: you could set a status variable
            return
        adc_value = float(received_bytes.decode("utf-8").strip())
        voltage = (adc_value / 1024.0) * REFERENCE_VOLTAGE
    except Exception:
        return

    with plot_lock:
        plot_buffer.append(voltage)
    with inference_lock:
        inference_buffer.append(voltage)


def ble_feed_thread_func(peripheral):
    """Keeps the BLE subscription alive. Notification callback appends data."""
    try:
        peripheral.notify(SERVICE_UUID, CHARACTERISTIC_UUID, ble_notification_callback)
        # Keep thread alive while connected and not stopped
        while not stop_event.is_set() and peripheral.is_connected():
            time.sleep(0.2)
    except Exception:
        pass
    finally:
        try:
            if peripheral.is_connected():
                peripheral.disconnect()
        except Exception:
            pass


def scan_and_connect_device():
    """Scan for device and connect. Returns connected peripheral or None."""
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("No Bluetooth adapters found.")
        return None
    adapter = adapters[0]
    print(f"Using adapter: {adapter.identifier()} [{adapter.address()}]")
    print(f"Scanning for devices for {SCAN_DURATION} ms...")
    adapter.scan_for(SCAN_DURATION)
    peripherals = adapter.scan_get_results()
    for p in peripherals:
        print(f"Found: {p.identifier()} [{p.address()}]")
        if p.identifier() == DEVICE_IDENTIFIER:
            try:
                print(f"Connecting to {p.identifier()}...")
                p.connect()
                print("Connected.")
                return p
            except Exception as e:
                print(f"Failed to connect: {e}")
                return None
    print("Target device not found.")
    return None


def simulated_feed_thread_func(rate_hz=20):
    """Generate an ECG-like waveform with noise and occasional pulses."""
    t = 0.0
    dt = 1.0 / rate_hz
    while not stop_event.is_set():
        # synthetic ECG-like baseline + QRS-like spikes
        baseline = 1.8 + 0.2 * np.sin(2 * np.pi * 1.0 * t)  # slow baseline wander
        qrs = 0.0
        # occasional spike pattern
        if random.random() < 0.02:
            qrs = 1.0 + 0.5 * random.random()
        noise = 0.05 * np.random.randn()
        voltage = float(np.clip(baseline + qrs + noise, 0.0, 4.0))
        with plot_lock:
            plot_buffer.append(voltage)
        with inference_lock:
            inference_buffer.append(voltage)
        t += dt
        time.sleep(dt)


# ---------------- Inference worker ----------------
def inference_worker_func():
    """Runs in background. When enough data in inference_buffer, runs predictor.get_prediction on a copy."""
    global _last_prediction
    while not stop_event.is_set():
        # wait a tiny bit
        time.sleep(0.05)
        # Trigger only if we have enough samples (or you can always run on whatever is present)
        should_run = False
        with inference_lock:
            cur_len = len(inference_buffer)
            if cur_len >= 10:  # minimal useful size
                # Run inference every INFERENCE_TRIGGER_COUNT new samples
                # Use a simple policy: run if buffer length increased by trigger count OR every fixed interval
                # For simplicity: run if len >= INFERENCE_WINDOW_SIZE OR random small chance to avoid lockstep
                if cur_len >= INFERENCE_WINDOW_SIZE or cur_len % INFERENCE_TRIGGER_COUNT == 0:
                    data_for_infer = list(inference_buffer)
                    should_run = True
                else:
                    should_run = False
        if should_run:
            try:
                # Predictor will resample internally to the required length
                pred = predictor_obj.get_prediction(data_for_infer)
                with inference_lock:
                    _last_prediction = pred
            except Exception as e:
                with inference_lock:
                    _last_prediction = f"Error: {e}"


# ---------------- Plot generator for Gradio streaming ----------------
def make_ecg_figure():
    with plot_lock:
        y = list(plot_buffer)
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(range(len(y)), y, color="red")
    ax.set_ylim(PLOT_RANGE)
    ax.set_xlim(0, MAX_POINTS - 1)
    ax.set_xlabel("Samples")
    ax.set_ylabel("Voltage (V)")
    ax.set_title(f"Live ECG (mean={np.mean(y):.2f} V)")
    ax.grid(True)
    fig.tight_layout()
    return fig


def stream_plot_and_pred():
    """Generator that yields (figure, prediction_text) tuples for gradio.load streaming."""
    while not stop_event.is_set():
        fig = make_ecg_figure()
        with inference_lock:
            pred = _last_prediction
        yield (fig, pred)
        time.sleep(PLOT_UPDATE_INTERVAL)
    # final yield once to let UI settle
    fig = make_ecg_figure()
    with inference_lock:
        pred = _last_prediction
    yield (fig, pred)


# ---------------- Main: console choice then launch Gradio ----------------
def main():
    global ecg_device

    print("Select mode before launching UI:")
    print("1) Use real BLE device (scan & connect before UI)")
    print("2) Use simulated ECG feed (start simulated feed before UI)")
    print("3) Skip data feed (UI preview only)")
    choice = input("Enter 1/2/3: ").strip()

    # Start appropriate feed
    feed_thread = None
    infer_thread = None

    if choice == "1":
        print("Scanning and connecting to BLE device...")
        ecg_device = scan_and_connect_device()
        if ecg_device is None:
            print("BLE connect failed or device not found. Falling back to simulated feed.")
            feed_thread = threading.Thread(target=simulated_feed_thread_func, daemon=True)
            feed_thread.start()
        else:
            # start ble feed thread to subscribe and keep alive
            feed_thread = threading.Thread(target=ble_feed_thread_func, args=(ecg_device,), daemon=True)
            feed_thread.start()
    elif choice == "2":
        print("Starting simulated ECG feed...")
        feed_thread = threading.Thread(target=simulated_feed_thread_func, daemon=True)
        feed_thread.start()
    else:
        print("Skipping data feed. UI preview only (no data will arrive).")

    # Start inference worker thread (always start; it will be idle if no data)
    infer_thread = threading.Thread(target=inference_worker_func, daemon=True)
    infer_thread.start()

    # Build Gradio UI
    with gr.Blocks(title="Live ECG Monitor") as demo:
        gr.Markdown("# ArrythmiX")
        gr.Markdown("Live ECG Plot and Classification")
        with gr.Row():
            ecg_plot = gr.Plot(label="ECG Plot")
            pred_box = gr.Textbox(label="Classification", interactive=False)

        # Stop button to stop threads and disconnect BLE
        def stop_and_disconnect():
            stop_event.set()
            # try to disconnect BLE device politely
            try:
                if ecg_device and getattr(ecg_device, "is_connected", lambda: False)():
                    ecg_device.disconnect()
            except Exception:
                pass
            return "Stopped."

        stop_btn = gr.Button("Stop & Disconnect")
        stop_status = gr.Textbox(label="Stop status", interactive=False)

        # stream generator outputs (plot, prediction)
        demo.load(stream_plot_and_pred, inputs=None, outputs=[ecg_plot, pred_box], stream_every=PLOT_UPDATE_INTERVAL)

        stop_btn.click(stop_and_disconnect, inputs=None, outputs=stop_status)

    # Launch UI (blocks until closed)
    demo.launch()


if __name__ == "__main__":
    main()
