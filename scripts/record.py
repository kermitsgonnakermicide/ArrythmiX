import time

import serial
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

# === Configuration ===
PORT = '/dev/ttyACM0'      # Replace with your port (e.g., COM3 on Windows)
BAUD_RATE = 115200
MAX_POINTS = 200           # Number of points to show in the plot window
PLOT_RANGE = (0, 1024)     # Y-axis range

# === Setup Serial ===
ser = serial.Serial(PORT, BAUD_RATE, timeout=1)

# === Setup Plot ===
data = deque([0] * MAX_POINTS, maxlen=MAX_POINTS)
fig, ax = plt.subplots()
line, = ax.plot(data)
ax.set_ylim(PLOT_RANGE)
ax.set_title("Live Serial Data")
ax.set_xlabel("Time")
ax.set_ylabel("Value")
f = open("recordings.txt", "r")
f = f.readlines()
# === Update Function ===
def update(frame):
    for i in f:
        data.append(i)
        time.sleep(0.01)
    line.set_ydata(data)
    return line,

# === Live Animation ===
ani = FuncAnimation(fig, update, interval=50)
plt.show()
