import math
from datetime import datetime, timezone

import joblib
import numpy as np


MODEL_PATH = "app/ml/xgboost_goal_predictor.pkl"

FEATURE_NAMES = [
    "dist_to_goal",
    "angle_to_goal",
    "time_remaining",
    "in_penalty_box",
    "type_Ball Receipt*",
    "type_Ball Recovery",
    "type_Block",
    "type_Carry",
    "type_Clearance",
    "type_Dispossessed",
    "type_Dribble",
    "type_Duel",
    "type_Foul Committed",
    "type_Foul Won",
    "type_Goal Keeper",
    "type_Miscontrol",
    "type_Pass",
    "type_Pressure",
    "type_Shot",
    "play_From Corner",
    "play_From Counter",
    "play_From Free Kick",
    "play_From Goal Kick",
    "play_From Keeper",
    "play_From Kick Off",
    "play_From Throw In",
    "play_Other",
    "play_Regular Play",
]

GOAL_X = 105.0
GOAL_Y = 34.0
PENALTY_BOX_X = 88.0
MATCH_DURATION = 5400.0


class MatchPredictor:

    def __init__(self):
        self.model = joblib.load(MODEL_PATH)

    def _event_type_onehot(self, event_type: str) -> dict[str, int]:
        mapping = {
            "pass": "type_Pass",
            "shot": "type_Shot",
            "tackle": "type_Duel",
            "dribble": "type_Dribble",
            "save": "type_Goal Keeper",
            "ball_receipt": "type_Ball Receipt*",
            "ball_recovery": "type_Ball Recovery",
            "block": "type_Block",
            "carry": "type_Carry",
            "clearance": "type_Clearance",
            "dispossessed": "type_Dispossessed",
            "foul_committed": "type_Foul Committed",
            "foul_won": "type_Foul Won",
            "miscontrol": "type_Miscontrol",
            "pressure": "type_Pressure",
        }
        mapped = mapping.get(event_type.lower().replace(" ", "_"), "type_Pass")
        onehot = {f: 0 for f in FEATURE_NAMES if f.startswith("type_")}
        if mapped in onehot:
            onehot[mapped] = 1
        return onehot

    def _play_pattern_onehot(self) -> dict[str, int]:
        onehot = {f: 0 for f in FEATURE_NAMES if f.startswith("play_")}
        onehot["play_Regular Play"] = 1
        return onehot

    def _event_to_vector(self, event: dict, min_ts: datetime | None) -> list[float]:
        x = event["x"]
        y = event["y"]

        dist_to_goal = math.sqrt((GOAL_X - x) ** 2 + (GOAL_Y - y) ** 2)
        angle_to_goal = math.atan2(GOAL_Y - y, GOAL_X - x)
        in_penalty_box = 1.0 if x >= PENALTY_BOX_X else 0.0

        if min_ts is not None:
            try:
                ts = event["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                elapsed = (ts - min_ts).total_seconds()
                time_remaining = max(MATCH_DURATION - elapsed, 0.0)
            except Exception:
                time_remaining = MATCH_DURATION
        else:
            time_remaining = MATCH_DURATION

        type_oh = self._event_type_onehot(event.get("event_type", "pass"))
        play_oh = self._play_pattern_onehot()

        row = {
            "dist_to_goal": dist_to_goal,
            "angle_to_goal": angle_to_goal,
            "time_remaining": time_remaining,
            "in_penalty_box": in_penalty_box,
            **type_oh,
            **play_oh,
        }

        return [row[f] for f in FEATURE_NAMES]

    def _parse_timestamp(self, event: dict) -> datetime | None:
        try:
            ts = event["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            return ts
        except Exception:
            return None

    async def predict_goal_probability(self, match_state: list[dict]) -> dict:
        if not match_state:
            return {"goal_prob": 0.0, "momentum": "neutral"}

        timestamps = [self._parse_timestamp(e) for e in match_state]
        valid_ts = [t for t in timestamps if t is not None]
        min_ts = min(valid_ts) if valid_ts else None

        X = np.array(
            [self._event_to_vector(e, min_ts) for e in match_state],
            dtype=np.float32,
        )

        probas = self.model.predict_proba(X)
        goal_probs = probas[:, 1]
        max_goal_prob = float(goal_probs.max())

        if max_goal_prob > 0.15:
            momentum = "attacking"
        elif max_goal_prob < 0.05:
            momentum = "neutral"
        else:
            momentum = "balanced"

        return {"goal_prob": round(max_goal_prob, 4), "momentum": momentum}
