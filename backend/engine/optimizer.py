import numpy as np
from typing import List, Dict, Any, Tuple, Union
from .database import VectorDB

class CurveInterpreter:
    def __init__(self, curve_data: List[Dict[str, float]]):
        """
        curve_data: List of dicts with 'time' (0.0 to 1.0) and 'value' (0.0 to 1.0)
        e.g., [{'time': 0.0, 'value': 1.0}, {'time': 0.5, 'value': 0.2}, ...]
        """
        self.curve_data = sorted(curve_data, key=lambda x: x['time'])

    def get_value_at(self, t: float) -> float:
        """
        Interpolates the curve value at normalized time t (0.0 to 1.0).
        """
        if not self.curve_data:
            return 0.0

        if t <= self.curve_data[0]['time']:
            return self.curve_data[0]['value']
        if t >= self.curve_data[-1]['time']:
            return self.curve_data[-1]['value']

        # Linear interpolation
        for i in range(len(self.curve_data) - 1):
            p1 = self.curve_data[i]
            p2 = self.curve_data[i+1]
            if p1['time'] <= t <= p2['time']:
                ratio = (t - p1['time']) / (p2['time'] - p1['time'])
                return p1['value'] + ratio * (p2['value'] - p1['value'])

        return 0.0

def get_bell_shape_weight(t: float, nodes: List[Dict[str, float]]) -> float:
    """
    Generates a combined Bell-shape (Gaussian) weight for filters.
    t: normalized time (0.0 to 1.0)
    nodes: List of dicts, each containing 'peak_t', 'sigma', 'amplitude'.

    Returns: value between 0.0 and 1.0 (Sum of Gaussians, clamped).
    """
    if not nodes:
        return 0.0

    total_weight = 0.0
    for node in nodes:
        peak_t = node.get('peak_t', 0.5)
        sigma = node.get('sigma', 0.1)
        amplitude = node.get('amplitude', 1.0)

        # Gaussian formula
        val = amplitude * np.exp(-((t - peak_t)**2) / (2 * sigma**2))
        total_weight += val

    return min(total_weight, 1.0)

def match_clips_to_curve(
    curve_data: List[Dict[str, float]],
    vector_db: VectorDB,
    target_length_sec: float,
    clip_granularity_sec: float = 2.0,
    time_scaling_options: Dict[str, Any] = None,
    filter_nodes: List[Dict[str, float]] = None
) -> List[Dict[str, Any]]:
    """
    Generates an Edit Decision List (EDL) based on the similarity curve.

    Logic:
    - Divide target length into segments (granularity).
    - For each segment, calculate required similarity from curve.
    - If it's the first segment, pick a random start or high value logic.
    - For subsequent segments:
        - Get embedding of the previous chosen clip.
        - If curve value is HIGH (e.g. > 0.8), search for nearest neighbor (high cosine sim).
        - If curve value is LOW (e.g. < 0.2), search for furthest neighbor (low cosine sim) - or just random distinct.
        - For MID values, pick something in between or weighted random.
    """

    interpreter = CurveInterpreter(curve_data)
    num_segments = int(target_length_sec / clip_granularity_sec)
    edl = []

    current_vector = None
    last_clip_index = -1

    looping_enabled = time_scaling_options.get('looping', False) if time_scaling_options else False
    speed_factor = time_scaling_options.get('speed', 1.0) if time_scaling_options else 1.0

    # Ensure filter_nodes is a list if None
    if filter_nodes is None:
        filter_nodes = []

    for i in range(num_segments):
        t_normalized = i / max(num_segments, 1) # Avoid div by zero if length is super short
        if num_segments <= 1: t_normalized = 0.0

        curve_val = interpreter.get_value_at(t_normalized)

        # Determine duration based on speed factor (simplified)
        duration = clip_granularity_sec / speed_factor

        if current_vector is None:
            # First clip: Start with a random clip if no context
            # Or better, if curve_val is high, start with something "average" or "archetypal"?
            # For now, random is fine.
            random_query = np.random.rand(1, vector_db.dimension).astype('float32')
            random_query /= np.linalg.norm(random_query)
            _, results, indices = vector_db.search(random_query, k=1)

            if results and results[0]:
                best_match = results[0][0]
                best_index = indices[0][0]
            else:
                best_match = None
                best_index = -1
        else:
            # Check for looping logic: if previous clip wants to loop
            if looping_enabled and i > 0 and i % 2 == 0:
                 # Artificial looping: repeat previous clip
                 # In real scenario, we might want to just extend the duration instead of appending again
                 # But sticking to segment logic:
                 # We need to find the clip we used last time.
                 # Assuming we have its vector, we search for ITSELF (nearest is itself).
                 search_vector = current_vector
                 k = 1
                 distances, results, indices = vector_db.search(search_vector, k=k)
                 best_match = results[0][0]
                 best_index = indices[0][0]
            else:
                # Standard Similarity Logic
                search_vector = current_vector
                if curve_val < 0.3:
                    # Search for opposite content
                    search_vector = -current_vector

                k = 5
                distances, results, indices = vector_db.search(search_vector, k=k)
                candidates = results[0] # List of metadata dicts
                candidate_indices = indices[0]

                # Pick top match
                best_match = candidates[0]
                best_index = candidate_indices[0]

        if best_match is None or best_index == -1:
             continue

        # Reconstruct vector using the retrieved index
        try:
             current_vector = vector_db.index.reconstruct(int(best_index))
             current_vector = current_vector.reshape(1, -1)
        except Exception as e:
             # Fallback if reconstruction fails (e.g. index type doesn't support it)
             # but IndexFlatIP supports it.
             # print(f"Warning: Vector reconstruction failed: {e}")
             current_vector = np.random.rand(1, vector_db.dimension).astype('float32')
             current_vector /= np.linalg.norm(current_vector)

        clip_info = {
            "time_start": i * duration, # Adjusted for speed? Or timeline position?
            # If speed > 1, clips are shorter, so we fit more?
            # Or is this placement on timeline?
            # Let's assume placement on timeline is fixed by i * granularity,
            # but source duration is affected.
            "timeline_start": i * clip_granularity_sec,
            "duration": duration,
            "source_clip_id": best_match.get('filename', 'unknown'),
            "source_time": best_match.get('timestamp', 0.0),
            "similarity_score": curve_val,
            "filter_weight": get_bell_shape_weight(t_normalized, nodes=filter_nodes)
        }
        edl.append(clip_info)
        last_clip_index = best_index

    return edl
