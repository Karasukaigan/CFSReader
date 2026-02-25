import json
from natsort import natsorted
import os
import matplotlib.pyplot as plt

def calculate_color_from_freq(freq, min_freq=0.3, max_freq=2.5):
    """Calculate color based on frequency"""
    if freq <= min_freq:
        color = (0.5, 0.8, 1)  # Light blue
    elif freq >= max_freq:
        color = (1, 0, 0)  # Red
    else:
        # Gradient from light blue to red
        freq_ratio = (freq - min_freq) / (max_freq - min_freq)
        r = 0.5 + 0.5 * freq_ratio  # Red channel
        g = 0.8 - 0.8 * freq_ratio  # Green channel
        b = 1 - freq_ratio  # Blue channel
        color = (r, g, b)
    return color

def draw_single_sawtooth_segment(ax, data, key, start_x, end_x, seg_w, min_freq, max_freq, height):
    """Draw a single sawtooth segment"""
    try:
        params = data[key]
        
        # Check if necessary keys are present
        if not params or 'max' not in params or 'min' not in params or 'freq' not in params or 'decline_ratio' not in params:
            rect = plt.Rectangle((start_x, 0), seg_w, height, facecolor='black', edgecolor='none')
            ax.add_patch(rect)
            return
            
        max_val = params['max']
        min_val = params['min']
        freq = params['freq']
        decline_ratio = params['decline_ratio']

        # Calculate color
        color = calculate_color_from_freq(freq, min_freq, max_freq)

        if decline_ratio <= 0:
            decline_ratio = 1e-6
        elif decline_ratio >= 1:
            decline_ratio = 1 - 1e-6

        total_cycles = freq * 3.0  # Total cycles in 3 seconds
        key_points_x = []  # Key point x coordinates
        key_points_y = []  # Key point y coordinates
        
        # Add starting point
        key_points_x.append(start_x)
        y_max = (max_val / 100.0) * height
        y_min = (min_val / 100.0) * height
        key_points_y.append(y_max)
        
        # Generate key turning points for sawtooth wave
        current_x = start_x
        cycle_num = 0
        while current_x < end_x and cycle_num <= total_cycles:
            cycle_start_x = start_x + (cycle_num * seg_w) / total_cycles
            cycle_end_x = start_x + ((cycle_num + 1) * seg_w) / total_cycles
            
            if cycle_start_x >= end_x:
                break
            
            # If not the first cycle, add cycle start point (maximum value)
            if cycle_num > 0 and cycle_start_x > current_x and cycle_start_x < end_x:
                key_points_x.append(cycle_start_x)
                key_points_y.append(y_max)
            
            # Decline point (minimum value)
            decline_x = cycle_start_x + decline_ratio * (cycle_end_x - cycle_start_x)
            if decline_x > current_x and decline_x < end_x:
                key_points_x.append(decline_x)
                key_points_y.append(y_min)
            
            # If not the last cycle, add cycle end point (maximum value)
            if cycle_end_x < end_x:
                key_points_x.append(cycle_end_x)
                key_points_y.append(y_max)
            
            current_x = cycle_end_x
            cycle_num += 1
            
            # Prevent infinite loop
            if cycle_num > total_cycles + 1:
                break
        
        # Calculate actual y value at end_x position
        actual_rel_pos = (end_x - start_x) / seg_w  # Actual relative position
        actual_total_phase = actual_rel_pos * total_cycles
        current_cycle_phase = actual_total_phase - int(actual_total_phase)
        
        if current_cycle_phase < decline_ratio:
            # Decline phase
            decline_progress = current_cycle_phase / decline_ratio
            current_value = max_val - (max_val - min_val) * decline_progress
        else:
            # Rise phase
            rise_start_phase = decline_ratio
            rise_progress = (current_cycle_phase - rise_start_phase) / (1 - decline_ratio)
            current_value = min_val + (max_val - min_val) * rise_progress
        
        y_end = (current_value / 100.0) * height
        
        # Replace or add end point
        if key_points_x and abs(key_points_x[-1] - end_x) < 1e-6:
            key_points_y[-1] = y_end
        else:
            key_points_x.append(end_x)
            key_points_y.append(y_end)

        # Remove duplicates
        points = list(zip(key_points_x, key_points_y))
        unique_points = []
        for point in points:
            if not unique_points or abs(point[0] - unique_points[-1][0]) > 1e-6:
                unique_points.append(point)
        
        if len(unique_points) > 1:
            unique_x, unique_y = zip(*unique_points)
            ax.plot(unique_x, unique_y, color=color, linewidth=1, antialiased=True)
    except (KeyError, TypeError, ValueError) as e:
        print(f"Error processing key {key}: {e}")
        rect = plt.Rectangle((start_x, 0), seg_w, height, facecolor='black', edgecolor='none')
        ax.add_patch(rect)

def draw_sawtooth_waves(data, output_file=None, dpi=100):
    """Draw sawtooth wave image based on input dictionary"""
    data = sort_dict_keys_naturally(data)

    WIDTH, HEIGHT = 2000, 100  # Chart width and height, not equal to actual output image dimensions
    figsize = (WIDTH/dpi, HEIGHT/dpi)
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_xlim(0, WIDTH)
    ax.set_ylim(0, HEIGHT)
    ax.axis('off')
    
    keys = list(data.keys())
    num_keys = len(keys)
    if num_keys == 0:
        ax.set_facecolor('black')
        if output_file:
            save_as_png(fig, output_file)
        return fig

    base_w = WIDTH // num_keys  # Base width per segment
    remainder = WIDTH % num_keys  # Remaining width
    MIN_FREQ = 0.3  # Minimum frequency
    MAX_FREQ = 2.5  # Maximum frequency

    start_x = 0
    for i, key in enumerate(keys):
        seg_w = base_w + 1 if i < remainder else base_w  # Current segment width
        end_x = start_x + seg_w
        draw_single_sawtooth_segment(ax, data, key, start_x, end_x, seg_w, MIN_FREQ, MAX_FREQ, HEIGHT)
        start_x = end_x

    ax.set_facecolor('black')
    if output_file:
        save_as_png(fig, output_file)
    return fig

def save_as_png(fig, filepath):
    """Save matplotlib figure object as PNG file"""
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fig.savefig(filepath, format='png', bbox_inches='tight', pad_inches=0,
                facecolor='black', edgecolor='none')
    return filepath

def sort_dict_keys_naturally(d):
    """Sort dictionary keys in natural order"""
    return {key: d[key] for key in natsorted(d.keys())}

def read_json_to_dict(file_path):
    """Read JSON file to dictionary"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return {}


if __name__ == "__main__":
    for file_path in [
        'test/test1.cfs',
        'test/test2.cfs',
        'test/test3.cfs',
        'test/test4.cfs',
    ]:
        data = read_json_to_dict(file_path)
        draw_sawtooth_waves(data, output_file=f'./{file_path.split("/")[-1]}.png')