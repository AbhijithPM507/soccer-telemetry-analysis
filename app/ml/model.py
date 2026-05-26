import random


class MatchPredictor:

    async def predict_goal_probability(self, match_state: list[dict]) -> dict:
        near_goal = sum(1 for event in match_state if event.get("x", 0) > 80)
        threat_score = min(near_goal / max(len(match_state), 1), 1.0)

        home_prob = round(0.3 + threat_score * 0.4 + random.uniform(-0.05, 0.05), 3)
        away_prob = round(1.0 - home_prob + random.uniform(-0.1, 0.1), 3)
        home_prob = max(0.0, min(1.0, home_prob))
        away_prob = max(0.0, min(1.0, away_prob))
        total = home_prob + away_prob
        if total > 0:
            home_prob = round(home_prob / total, 3)
            away_prob = round(away_prob / total, 3)

        if threat_score > 0.6:
            momentum = "home_attacking"
        elif threat_score < 0.2:
            momentum = "neutral"
        else:
            momentum = "balanced"

        return {"home_prob": home_prob, "away_prob": away_prob, "momentum": momentum}
