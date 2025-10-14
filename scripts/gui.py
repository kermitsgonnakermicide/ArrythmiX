import customtkinter
import simplepyble
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import threading
import numpy as np

from ml.runner import predictor

# === Configuration ===
MAX_POINTS = 200           # Number of points to show in the plot window
PLOT_RANGE = (0, 4)        # Y-axis range for voltage (V), adjust if necessary
SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "e2fd985e-ceb8-4ccb-9cd3-52563e4b5c62"
DEVICE_IDENTIFIER = "ECG Data"
REFERENCE_VOLTAGE = 3.7
SCAN_DURATION = 5000       # milliseconds

# --- Appearance ---
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")
plt.style.use('dark_background')

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Live ECG Data")
        self.geometry("1000x700")

        self.data = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
        self.predictor = predictor(MAX_POINTS)
        self.prediction_label_text = customtkinter.StringVar(value="Prediction: N/A")

        self.status_text = customtkinter.StringVar(value="Status: Initializing...")

        self._setup_ui()
        self._start_bluetooth_thread()

        self.ani = FuncAnimation(self.fig, self.update_plot, interval=50, blit=True)

    def _setup_ui(self):
        """Configures the main UI layout."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Main Frame ---
        main_frame = customtkinter.CTkFrame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # --- Matplotlib Figure ---
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot(self.data, color='#1f77b4')
        self.ax.set_ylim(PLOT_RANGE)
        self.ax.set_title("Live ECG Data")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Voltage (V)")
        self.fig.tight_layout()

        self.canvas = FigureCanvasTkAgg(self.fig, master=main_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        # --- Bottom Info Frame ---
        info_frame = customtkinter.CTkFrame(self)
        info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        # --- Prediction Label ---
        prediction_label = customtkinter.CTkLabel(info_frame, textvariable=self.prediction_label_text, font=("Roboto", 24, "bold"))
        prediction_label.grid(row=0, column=0, pady=10, padx=20, sticky="w")

        # --- Status Label ---
        status_label = customtkinter.CTkLabel(info_frame, textvariable=self.status_text, font=("Roboto", 16))
        status_label.grid(row=0, column=1, pady=10, padx=20, sticky="e")


        name_label = customtkinter.CTkLabel(info_frame,text="ArrhythmiX - Prototype 1", font=("Roboto", 24, "bold", "italic"), text_color="yellow")
        name_label.place(relx=0.5, rely=0.5, anchor="center")
    def _start_bluetooth_thread(self):
        """Initializes and starts the Bluetooth connection thread."""
        self.bt_thread = threading.Thread(target=self.start_bluetooth, daemon=True)
        self.bt_thread.start()
    window = 100
    def notification_callback(self, received_bytes):
        global window
        """Handles incoming data from the BLE characteristic."""
        if received_bytes == b"Leads Off":
            self.status_text.set("Status: Leads Off")
            return
        try:
            adc_value = float(received_bytes.decode('utf-8').strip())
            voltage = (adc_value / 4095) * REFERENCE_VOLTAGE
            self.data.append(voltage)
            if self.status_text == "Leads Off":
                self.status_text.set("Status: ECG Receiving")
            if len(self.data) >= MAX_POINTS:
                # prediction = self.predictor.get_prediction(list(self.data))
                self.prediction_label_text.set(f"Prediction: {"TBD"}")
                print("ran prediction")

        except (ValueError, UnicodeDecodeError):
            self.status_text.set(f"Status: Error decoding data")

    def update_plot(self, frame):
        """Updates the plot with new data."""
        self.line.set_ydata(self.data)
        return self.line,

    def start_bluetooth(self):
        """Scans for and connects to the ECG Bluetooth device."""
        self.status_text.set("Status: Searching for Bluetooth adapters...")
        adapters = simplepyble.Adapter.get_adapters()
        if not adapters:
            self.status_text.set("Status: No Bluetooth adapters found.")
            return

        adapter = adapters[0]
        self.status_text.set(f"Status: Using adapter: {adapter.identifier()}")

        self.status_text.set("Status: Scanning for devices...")
        adapter.scan_for(SCAN_DURATION)
        peripherals = adapter.scan_get_results()

        ecg_device = None
        for p in peripherals:
            if p.identifier() == DEVICE_IDENTIFIER:
                self.status_text.set(f"Status: Found device: {p.identifier()}")
                ecg_device = p
                break

        if not ecg_device:
            self.status_text.set(f"Status: Could not find device.")

            return

        try:
            self.status_text.set(f"Status: Connecting to {ecg_device.identifier()}...")
            ecg_device.connect()
            self.status_text.set("Status: Connected! Subscribing to notifications...")
            ecg_device.notify(SERVICE_UUID, CHARACTERISTIC_UUID, self.notification_callback)
            self.status_text.set("Status: Actively receiving ECG data.")

            while ecg_device.is_connected():
                pass # Keep thread alive

        except Exception as e:
            self.status_text.set(f"Status: Connection failed: {e}")
        finally:
            if ecg_device and ecg_device.is_connected():
                ecg_device.disconnect()
            self.status_text.set("Status: Disconnected.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
