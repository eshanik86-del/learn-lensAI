
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import defaultdict

from app.database import get_db
from app.models import Attempt
from app.services.predictor import predict_topic

router = APIRouter(
    prefix="/api/predictions",
    tags=["Predictions"]
)


@router.get("/")
def get_predictions(db: Session = Depends(get_db)):
    attempts = db.query(Attempt).order_by(Attempt.id).all()

    # Group attempts by topic
    topics = defaultdict(list)

    for attempt in attempts:
        topics[attempt.topic].append(attempt)

    results = []

    # Predict learning risk for each topic
    for topic, topic_attempts in topics.items():
        prediction = predict_topic(topic_attempts)

        results.append({
            "topic": topic,
            "total_attempts": len(topic_attempts),
            **prediction
        })

    return results
