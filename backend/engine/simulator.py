from typing import List, Dict, Any, Optional
import numpy as np

def find_clip_at_time(
    timestamp: float, # Normalized 0-1
    curve_data: List[Dict[str, float]],
    vector_db: Any,
    duration: float = 100.0,
    granularity: float = 2.0
) -> Optional[Dict[str, Any]]:
    """
    Simulates the clip selection logic up to the given timestamp to find the exact clip.
    This is a stateless simulation for preview purposes.
    """
    if not vector_db or len(vector_db.metadata) == 0:
        return None

    from .optimizer import CurveInterpreter
    interpreter = CurveInterpreter(curve_data)

    # Identify which segment index corresponds to timestamp
    # total segments = duration / granularity
    # current segment index = (timestamp * duration) / granularity

    target_idx = int((timestamp * duration) / granularity)

    # To be deterministic, we must replay the sequence from 0 to target_idx
    # Seed random for determinism if needed (though our logic uses curve_val deterministically mostly)
    # However, the *first* clip is random in match_clips_to_curve.
    # We should fix that seed based on curve hash or something?
    # For now, let's use a fixed seed per session or just fixed seed globally for preview consistency.
    np.random.seed(42)

    current_vector = None

    # We only care about the last one, but we need the chain.
    # Optimization: If target_idx is large, this loop might be slow (e.g. 1000 clips).
    # But for a few minutes of video (duration 100s, gran 2s => 50 clips), it's negligible (microseconds).

    final_match = None

    for i in range(target_idx + 1):
        t_norm = i * granularity / duration
        curve_val = interpreter.get_value_at(t_norm)

        if current_vector is None:
            # First clip: Random deterministically seeded
            random_query = np.random.rand(1, vector_db.dimension).astype('float32')
            random_query /= np.linalg.norm(random_query)
            _, results, indices = vector_db.search(random_query, k=1)
            if results and results[0]:
                final_match = results[0][0]
                idx = indices[0][0]
                current_vector = vector_db.index.reconstruct(int(idx)).reshape(1, -1)
        else:
            search_vector = current_vector
            if curve_val < 0.3:
                search_vector = -current_vector

            _, results, indices = vector_db.search(search_vector, k=5)
            # Pick first for determinism
            final_match = results[0][0]
            idx = indices[0][0]
            current_vector = vector_db.index.reconstruct(int(idx)).reshape(1, -1)

    return final_match
