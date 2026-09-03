from datetime import date


def recommend_courses(candidates, level, preferred_days, max_price):
    recommendations = []
    for candidate in candidates:
        remaining = candidate["capacity"] - candidate["enrolled"]
        breakdown = {
            "age": 30,
            "level": 25 if candidate["level"] in (level, "all_levels") else 0,
            "schedule": 20 if candidate["weekday"] in preferred_days else 0,
            "price": 15 if max_price is None or candidate["price"] <= max_price else 0,
            "availability": 10 if remaining >= 3 else 7 if remaining == 2 else 4,
        }
        recommendations.append({
            "class_id": candidate["class_id"],
            "course_id": candidate["course_id"],
            "course_name": candidate["course_name"],
            "coach_id": candidate["coach_id"],
            "coach_name": candidate["coach_name"],
            "weekday": candidate["weekday"],
            "start_time": candidate["start_time"],
            "price": candidate["price"],
            "remaining": remaining,
            "score": sum(breakdown.values()),
            "score_breakdown": breakdown,
        })
    return sorted(recommendations, key=lambda item: (-item["score"], item["price"], item["class_id"]))[:3]


def score_lead(trial_rating, latest_interaction_at, interaction_count, course_fit, purchase_intent, as_of):
    if latest_interaction_at:
        days_since_interaction = ((as_of or date.today()) - date.fromisoformat(latest_interaction_at[:10])).days
        recency = 20 if days_since_interaction <= 3 else 16 if days_since_interaction <= 7 else 10 if days_since_interaction <= 14 else 5 if days_since_interaction <= 30 else 0
    else:
        recency = 0
    breakdown = {
        "trial_rating": round(trial_rating / 5 * 25) if trial_rating is not None else 0,
        "recency": recency,
        "interaction_frequency": 20 if interaction_count >= 4 else 15 if interaction_count == 3 else 10 if interaction_count == 2 else 5 if interaction_count == 1 else 0,
        "course_fit": round(course_fit * 20),
        "purchase_intent": round(purchase_intent * 15),
    }
    score = sum(breakdown.values())
    return {"score": score, "level": "high" if score >= 80 else "medium" if score >= 60 else "low", "breakdown": breakdown}
