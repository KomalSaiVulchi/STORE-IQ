"""OSNet-based appearance embeddings and ReID matching."""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import orjson
import redis
import torch
from torchreid import models
from torchvision import transforms

from detector.visitor_id import new_visitor_id

logger = logging.getLogger("storeiq-pipeline")


@dataclass
class ReIDResult:
    """ReID match result."""

    visitor_id: str
    similarity: float
    is_new: bool


class ReIDEngine:
    """Cross-camera identity resolution using appearance embeddings."""

    def __init__(self, redis_url: str) -> None:
        """Initialize the ReID engine with Redis-backed embedding store."""
        self._redis = redis.Redis.from_url(redis_url, decode_responses=True)
        self._similarity_threshold = float(os.getenv("REID_SIMILARITY_THRESHOLD", "0.75"))
        self._max_gap = int(os.getenv("REID_MAX_GAP_SECONDS", "3600"))
        self._ttl = int(os.getenv("REID_TTL_SECONDS", "3600"))
        self._adjacent = self._load_adjacency()
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model = models.build_model(name="osnet_x1_0", num_classes=1000, pretrained=True)
        self._model.eval().to(self._device)
        self._preprocess = transforms.Compose(
            [
                transforms.ToPILImage(),
                transforms.Resize((256, 128)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
        # Local embedding cache keyed by track_id to avoid redundant inference
        self._embedding_cache: Dict[int, np.ndarray] = {}

    def resolve(
        self,
        embedding: np.ndarray,
        camera_id: str,
        seen_at: float,
        exclude_visitor_ids: Optional[Set[str]] = None,
    ) -> ReIDResult:
        """Resolve an embedding to an existing or new visitor id."""
        exclude = exclude_visitor_ids or set()
        best_id, best_score = self._search(embedding, camera_id, seen_at)
        if best_id and best_score >= self._similarity_threshold and best_id not in exclude:
            self._store_embedding(best_id, embedding, camera_id, seen_at)
            return ReIDResult(visitor_id=best_id, similarity=best_score, is_new=False)

        new_id = new_visitor_id()
        self._store_embedding(new_id, embedding, camera_id, seen_at)
        return ReIDResult(visitor_id=new_id, similarity=0.0, is_new=True)

    def _search(self, embedding: np.ndarray, camera_id: str, seen_at: float) -> tuple[Optional[str], float]:
        """Search Redis for the closest embedding using SCAN (non-blocking)."""
        best_id: Optional[str] = None
        best_score = 0.0

        # Use SCAN instead of KEYS to avoid blocking Redis
        cursor = 0
        while True:
            cursor, keys = self._redis.scan(cursor=cursor, match="reid:*", count=100)
            for key in keys:
                raw = self._redis.get(key)
                if not raw:
                    continue
                try:
                    payload = orjson.loads(raw)
                except (orjson.JSONDecodeError, TypeError):
                    continue
                time_gap = seen_at - payload.get("seen_at", 0)
                if time_gap > self._max_gap:
                    continue
                last_camera = payload.get("camera_id")
                if last_camera and not self._is_adjacent(last_camera, camera_id):
                    continue
                other = np.array(payload.get("embedding", []), dtype=np.float32)
                if other.size == 0:
                    continue
                score = self._cosine_similarity(embedding, other)
                if score > best_score:
                    best_id = payload.get("visitor_id")
                    best_score = score

            if cursor == 0:
                break

        return best_id, best_score

    def _is_adjacent(self, left: str, right: str) -> bool:
        """Return True if two cameras are adjacent or identical."""
        if left == right:
            return True
        return right in self._adjacent.get(left, [])

    @staticmethod
    def _load_adjacency() -> Dict[str, List[str]]:
        """Load adjacent camera mappings from env or store_layout.json."""
        raw = os.getenv("ADJACENT_CAMERAS_JSON", "")
        if raw:
            try:
                return orjson.loads(raw)
            except orjson.JSONDecodeError:
                pass

        layout_paths = [
            Path("/app/pipeline/store_layout.json"),
            Path(__file__).resolve().parent.parent / "pipeline" / "store_layout.json",
        ]
        for path in layout_paths:
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text())
                store = data.get("stores", [{}])[0]
                cameras = store.get("cameras", [])
                adjacency: Dict[str, List[str]] = {}
                ids = [cam["camera_id"] for cam in cameras]
                for idx, cam in enumerate(cameras):
                    cam_id = cam["camera_id"]
                    neighbors = []
                    if idx > 0:
                        neighbors.append(ids[idx - 1])
                    if idx + 1 < len(ids):
                        neighbors.append(ids[idx + 1])
                    adjacency[cam_id] = neighbors
                return adjacency
            except (json.JSONDecodeError, KeyError, IndexError):
                continue
        return {}

    def _store_embedding(self, visitor_id: str, embedding: np.ndarray, camera_id: str, seen_at: float) -> None:
        """Persist embedding to Redis with TTL."""
        payload = {
            "visitor_id": visitor_id,
            "camera_id": camera_id,
            "seen_at": seen_at,
            "embedding": embedding.tolist(),
        }
        try:
            self._redis.setex(f"reid:{visitor_id}", self._ttl, orjson.dumps(payload))
        except redis.RedisError as exc:
            logger.warning("Failed to store ReID embedding: %s", exc)

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
        return float(np.dot(a, b) / denom)

    def extract_embedding(self, frame: np.ndarray, bbox: tuple[int, int, int, int], track_id: int = -1) -> np.ndarray:
        """Extract an OSNet embedding for the given bounding box.

        Args:
            frame: BGR image array.
            bbox: Bounding box (x1, y1, x2, y2).
            track_id: Optional track ID for embedding caching.

        Returns:
            512-d embedding vector.
        """
        # Check cache first (skip redundant inference for same track)
        if track_id >= 0 and track_id in self._embedding_cache:
            return self._embedding_cache[track_id]

        x1, y1, x2, y2 = bbox
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return np.zeros(512, dtype=np.float32)
        tensor = self._preprocess(crop).unsqueeze(0).to(self._device)
        with torch.no_grad():
            embedding = self._model(tensor)
        vector = embedding.squeeze(0).cpu().numpy().astype(np.float32)

        # Cache the embedding for this track
        if track_id >= 0:
            self._embedding_cache[track_id] = vector
            # Limit cache size to prevent memory leaks
            if len(self._embedding_cache) > 500:
                oldest_keys = sorted(self._embedding_cache.keys())[:250]
                for key in oldest_keys:
                    self._embedding_cache.pop(key, None)

        return vector

    def clear_track_cache(self, track_id: int) -> None:
        """Remove a track from the embedding cache."""
        self._embedding_cache.pop(track_id, None)
