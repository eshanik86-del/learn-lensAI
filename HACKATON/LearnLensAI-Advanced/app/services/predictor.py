
def predict_topic(attempts):
    """
    Estimate learning difficulty using historical performance,
    recent mistakes, and consecutive incorrect answers.
    """

    total = len(attempts)

    if total < 5:
        return {
            "risk_score": None,
            "risk_level": "Insufficient data",
            "explanation": (
                f"Only {total} attempt(s) recorded. "
                "More attempts are needed to identify a pattern."
            ),
            "recommendation": (
                "Try 3-5 questions at different difficulty levels."
            ),
            "trend": "Not enough data",
        }

    weights = {
        "easy": 1.0,
        "medium": 1.25,
        "hard": 1.5,
    }

    ordered = sorted(attempts, key=lambda a: a.id)
    recent = ordered[-5:]

    total_weight = sum(
        weights.get(a.difficulty.lower(), 1.0)
        for a in ordered
    )

    error_weight = sum(
        weights.get(a.difficulty.lower(), 1.0)
        for a in ordered
        if not a.is_correct
    )

    historical_error = error_weight / total_weight * 100

    recent_error = (
        sum(not a.is_correct for a in recent)
        / len(recent)
        * 100
    )

    streak = 0
    for attempt in reversed(ordered):
        if attempt.is_correct:
            break
        streak += 1

    streak_risk = min(streak / 3, 1) * 100

    if len(ordered) >= 4:
        midpoint = len(ordered) // 2

        earlier_accuracy = (
            sum(a.is_correct for a in ordered[:midpoint])
            / midpoint
            * 100
        )

        later = ordered[midpoint:]
        later_accuracy = (
            sum(a.is_correct for a in later)
            / len(later)
            * 100
        )

        improvement = later_accuracy - earlier_accuracy
    else:
        improvement = 0

    score = (
        historical_error * 0.40
        + recent_error * 0.35
        + streak_risk * 0.25
    )

    if improvement > 0:
        score -= min(improvement * 0.30, 20)

    score = round(max(0, min(100, score)))

    if improvement >= 20:
        trend = "Improving"
    elif improvement <= -20:
        trend = "Declining"
    else:
        trend = "Stable"

    if score >= 60:
        level = "High"
        recommendation = (
            "Review the fundamentals and solve 5 easy questions. "
            "Then retry medium questions and review each mistake."
        )
    elif score >= 30:
        level = "Medium"
        recommendation = (
            "Review the concepts you missed and complete "
            "5 targeted practice questions."
        )
    else:
        level = "Low"
        recommendation = (
            "Continue with mixed-difficulty practice to maintain "
            "your understanding."
        )

    if trend == "Improving":
        recommendation += (
            " Your recent performance is improving; "
            "gradually increase question difficulty."
        )

    return {
        "risk_score": score,
        "risk_level": level,
        "explanation": (
            f"Historical weighted error: {historical_error:.1f}%. "
            f"Recent error rate: {recent_error:.1f}%. "
            f"Consecutive mistakes: {streak}. "
            f"Accuracy change between earlier and later attempts: "
            f"{improvement:+.1f} percentage points."
        ),
        "recommendation": recommendation,
        "trend": trend,
    }
