import matplotlib.pyplot as plt
import numpy as np
import json
from matplotlib.animation import FuncAnimation
from collections import deque

# Configuration
ECG_HZ = 360.0
DATA_FILE = 'data.text'
MAX_POINTS = 500  # Number of points to display on the plot at once
PLOT_RANGE = (0, 4) # Y-axis range

def parse_data_from_file(filename):
    """Parses ECG data from a text file."""
    try:
        with open(filename, 'r') as f:
            content = f.read().strip()
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return []

    # Try parsing as JSON first
    try:
        json_data = json.loads(content)
        if 'data' in json_data and isinstance(json_data['data'], list):
            return json_data['data']
    except json.JSONDecodeError:
        # Not a JSON file, proceed to other formats
        pass

    # Expected format is like: deque([0.1, 0.2, 0.3])
    if content.startswith('deque(['):
        content = content[len('deque(['):-2] # Remove deque wrapper

    try:
        data = [float(x) for x in content.split(',')]
        return data
    except ValueError:
        print("Could not parse data. Ensure it's a comma-separated list of numbers, a deque representation, or a JSON object with a 'data' key.")
        return []


if __name__ == "__main__":
    all_ecg_data = parse_data_from_file(DATA_FILE)
    if not all_ecg_data:
        print(f"Could not read or parse data from {DATA_FILE}")
        exit()

    data_iterator = iter(all_ecg_data)
    
    # Setup Data and Plot
    plot_data = deque([0.0] * MAX_POINTS, maxlen=MAX_POINTS)
    
    fig, ax = plt.subplots()
    line, = ax.plot(plot_data)
    ax.set_ylim(PLOT_RANGE)
    ax.set_title("Live ECG Data Simulation")
    ax.set_xlabel("Time")
    ax.set_ylabel("Voltage (V)")

    def update(frame):
        global data_iterator
        try:
            # Get the next data point
            next_val = next(data_iterator)
            plot_data.append(next_val)
            line.set_ydata(plot_data)
        except StopIteration:
            # Stop the animation if there is no more data
            print("End of data stream.")
            data_iterator = iter(all_ecg_data)

        return line,

    # The interval should be 1000ms / 360Hz ~= 2.77 ms.
    ani = FuncAnimation(fig, update, interval=1000/ECG_HZ, blit=True)
    plt.show()
