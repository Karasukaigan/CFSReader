import json
from natsort import natsorted
import os
import math
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO

def calculate_color_from_freq(freq, min_freq=0.5, max_freq=2.5):
    """Calculate color based on frequency"""
    t = (freq - min_freq) / (max_freq - min_freq)
    t = max(0.0, min(1.0, t))
    start_color = (0.4, 0.8, 1.0)  # Light blue
    end_color   = (1.0, 0.0, 0.0)  # Red
    r = start_color[0] + t * (end_color[0] - start_color[0])
    g = start_color[1] + t * (end_color[1] - start_color[1])
    b = start_color[2] + t * (end_color[2] - start_color[2])
    return (r, g, b)

def generate_sawtooth_points(start_pos=None, start_trend=-1, max_val=50, min_val=50, freq=1.0, decline_ratio=0.5, total_time=5000):
    """Generate sawtooth wave curve key points"""
    if start_pos is None:
        start_pos = max_val
    if min_val > max_val:
        min_val, max_val = max_val, min_val
    if max_val == min_val:
        return {
            "x": [0, round(total_time)],
            "y": [start_pos, start_pos]
        }

    T = 1000.0 / freq  # Period
    decline_time = T * decline_ratio
    rise_time = T - decline_time

    def value_at_phase(phase):
        """Calculate y value based on phase"""
        if phase < 0 or phase >= T:
            phase = phase % T
        if decline_time == 0:
            if phase == 0:
                return max_val
            else:
                return min_val + (max_val - min_val) * (phase / rise_time)
        elif rise_time == 0:
            if phase < decline_time:
                return max_val - (max_val - min_val) * (phase / decline_time)
            elif phase == decline_time:
                return min_val
            else:  # phase > decline_time
                return max_val
        else:
            if phase < decline_time:
                return max_val - (max_val - min_val) * (phase / decline_time)
            else:
                return min_val + (max_val - min_val) * ((phase - decline_time) / rise_time)

    def find_initial_phase():
        """Calculate initial phase offset"""
        if max_val == min_val:
            return 0.0
        if decline_time == 0:
            if start_pos == max_val:
                return 0.0
            else:
                return (start_pos - min_val) / (max_val - min_val) * rise_time
        if rise_time == 0:
            if start_pos == min_val:
                return decline_time
            else:
                return (max_val - start_pos) / (max_val - min_val) * decline_time
        t_d = (max_val - start_pos) / (max_val - min_val) * decline_time
        t_r = decline_time + (start_pos - min_val) / (max_val - min_val) * rise_time
        if start_trend == -1:
            if 0 <= t_d <= decline_time:
                return t_d
            if start_pos == max_val:
                return 0.0
            if start_pos == min_val:
                return decline_time
            return t_d if t_d is not None else 0.0
        else:
            if decline_time <= t_r <= T:
                return t_r
            if start_pos == min_val:
                return decline_time
            if start_pos == max_val:
                return 0.0
            return t_r if t_r is not None else 0.0

    t_mod0 = find_initial_phase()

    events = []  # All event points

    # Max events
    k_min = math.ceil(t_mod0 / T)
    k_max = math.floor((total_time + t_mod0) / T)
    for k in range(k_min, k_max + 1):
        t = k * T - t_mod0
        if 0 < t <= total_time:
            events.append((t, max_val))

    # Min events
    k_min = math.ceil((t_mod0 - decline_time) / T)
    k_max = math.floor((total_time + t_mod0 - decline_time) / T)
    for k in range(k_min, k_max + 1):
        t = k * T + decline_time - t_mod0
        if 0 < t <= total_time:
            events.append((t, min_val))

    events.append((0.0, start_pos))  # Add start point
    end_phase = (t_mod0 + total_time) % T
    end_y = value_at_phase(end_phase)
    events.append((total_time, end_y))  # Add end point

    # Sort events
    if decline_ratio == 0:
        events.sort(key=lambda p: (p[0], -p[1]))
    elif decline_ratio == 1:
        events.sort(key=lambda p: (p[0], p[1]))
    else:
        events.sort(key=lambda p: p[0])

    # Remove duplicates
    unique_events = []
    for t, y in events:
        if unique_events and unique_events[-1][0] == t and unique_events[-1][1] == y:
            continue
        unique_events.append((t, y))

    # Convert to integer milliseconds
    x = [round(t) for t, _ in unique_events]
    y = [round(y, 2) for _, y in unique_events]

    return {"x": x, "y": y}

def merge_curve_points(segments):
    """Merge multiple curve segments into one continuous key point sequence"""
    if not segments:
        return {"x": [], "y": []}
    merged_x = []
    merged_y = []
    for i, seg in enumerate(segments):
        x_vals = seg["x"]
        y_vals = seg["y"]
        if i == 0:
            merged_x.extend(x_vals)
            merged_y.extend(y_vals)
        else:
            if len(x_vals) <= 1:
                continue
            offset = merged_x[-1]
            for x, y in zip(x_vals[1:], y_vals[1:]):
                merged_x.append(x + offset)
                merged_y.append(y)
    return {"x": merged_x, "y": merged_y}

def generate_curve_image(points, width=2000, height=100, bg_color=(0, 0, 0, 1), dpi=100):
    """Generate line chart image using matplotlib with anti-aliasing"""
    x_vals = points["x"]
    y_vals = points["y"]

    if not x_vals or not y_vals:
        from PIL import Image
        return Image.new("RGBA", (width, height), tuple(int(c * 255) for c in bg_color))

    fig_width_inch = width / dpi
    fig_height_inch = height / dpi
    fig, ax = plt.subplots(figsize=(fig_width_inch, fig_height_inch), dpi=dpi)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.axis('off')
    ax.set_xlim(min(x_vals), max(x_vals))
    ax.set_ylim(0, 100)

    for i in range(len(x_vals) - 1):
        x1, y1 = x_vals[i], y_vals[i]
        x2, y2 = x_vals[i+1], y_vals[i+1]
        dt = abs(x2 - x1)
        freq = 10.0 if dt == 0 else 1000.0 / dt
        r, g, b = calculate_color_from_freq(freq / 2)
        color = (r, g, b, 1.0)
        ax.plot([x1, x2], [y1, y2], color=color, linewidth=1, antialiased=True)

    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0, facecolor=bg_color, edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    from PIL import Image
    img = Image.open(buf).convert("RGBA")
    if img.size != (width, height):
        img = img.resize((width, height), Image.LANCZOS)
    return img

def draw_sawtooth_waves(data, output_file=None):
    """Draw sawtooth wave image based on input dictionary"""
    data = sort_dict_keys_naturally(data)
    segments = []
    segment_duration = 3000
    current_pos = 50
    for key, value in data.items():
        if not value:
            segments.append({"x": [0, segment_duration], "y": [current_pos, current_pos]})
        else:
            points = generate_sawtooth_points(start_pos=current_pos, max_val=value["max"], min_val=value["min"], freq=value["freq"], decline_ratio=value["decline_ratio"], total_time=segment_duration)
            segments.append(points)
            current_pos = points["y"][-1]
    fig = generate_curve_image(merge_curve_points(segments), 2000, 100)
    save_as_png(fig, output_file)
    return fig

def save_as_png(fig, file_path):
    """Save matplotlib figure object as PNG file"""
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    fig.save(file_path, format='PNG')

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
    pass