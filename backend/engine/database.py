import numpy as np
import faiss
import pickle
import os
from typing import List, Dict, Any, Tuple

class VectorDB:
    def __init__(self, dimension: int):
        self.dimension = dimension
        # Inner Product (IP) is equivalent to Cosine Similarity if vectors are normalized
        self.index = faiss.IndexFlatIP(dimension)
        self.metadata: List[Dict[str, Any]] = []

    def add(self, vectors: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        Add vectors to the index.
        vectors: shape (N, dimension)
        metadata: list of N dictionaries
        """
        if vectors.shape[1] != self.dimension:
            raise ValueError(f"Vector dimension mismatch. Expected {self.dimension}, got {vectors.shape[1]}")
        if len(vectors) != len(metadata):
            raise ValueError("Number of vectors and metadata items must match.")

        # FAISS expects float32
        vectors = vectors.astype('float32')
        self.index.add(vectors)
        self.metadata.extend(metadata)

    def search(self, query_vector: np.ndarray, k: int = 5) -> Tuple[np.ndarray, List[List[Dict[str, Any]]], List[List[int]]]:
        """
        Search for nearest neighbors.
        query_vector: shape (1, dimension) or (N, dimension)
        Returns: (distances, results_metadata_list, results_indices_list)
        """
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)

        query_vector = query_vector.astype('float32')
        distances, indices = self.index.search(query_vector, k)

        results_meta = []
        results_indices = []

        for row_indices in indices:
            row_meta = []
            row_idx = []
            for idx in row_indices:
                if idx != -1 and idx < len(self.metadata):
                    row_meta.append(self.metadata[idx])
                    row_idx.append(int(idx))
                else:
                    row_meta.append(None)
                    row_idx.append(-1)
            results_meta.append(row_meta)
            results_indices.append(row_idx)

        return distances, results_meta, results_indices

    def save(self, path: str):
        faiss.write_index(self.index, path + ".index")
        with open(path + ".meta", 'wb') as f:
            pickle.dump(self.metadata, f)

    def load(self, path: str):
        if os.path.exists(path + ".index"):
            self.index = faiss.read_index(path + ".index")
        if os.path.exists(path + ".meta"):
            with open(path + ".meta", 'rb') as f:
                self.metadata = pickle.load(f)
