import time

def simulate_live_feed(data, chunk_size, delay=0.01):
    """
    Simulates receiving data in chunks, similar to a live stream.

    Args:
        data (np.ndarray): The complete dataset to simulate the stream from.
        chunk_size (int): The number of data points in each chunk.
        delay (float): The delay in seconds between yielding chunks.
    """
    num_chunks = len(data) // chunk_size
    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = start_index + chunk_size
        yield data[start_index:end_index]
        time.sleep(delay)

    # Yield the last chunk if there's any remaining data
    if len(data) % chunk_size != 0:
        yield data[num_chunks * chunk_size:]