from app.db import load_messages
from collections import Counter
import datetime
from app.ml_sentiment import predict_sentiment


def get_analytics(room):
    messages = load_messages(room)
    sentiment = get_sentiment_ml(messages)

    if not messages:
        return "No data available."

    user_count = Counter()
    hour_count = Counter()

    for msg in messages:
        user = msg["username"]
        ts = msg["timestamp"]

        user_count[user] += 1

        hour = datetime.datetime.fromtimestamp(ts).strftime("%H")
        hour_count[hour] += 1

    top_user = user_count.most_common(1)[0]
    peak_hour = hour_count.most_common(1)[0]

    result = "📊 Chat Analytics\n\n"

    result += "👥 Messages per user:\n"
    for user, count in user_count.items():
        result += f"• {user}: {count}\n"

    result += f"\n🔥 Most active user: {top_user[0]} ({top_user[1]} msgs)"
    result += f"\n⏰ Peak hour: {peak_hour[0]}:00"
    result += f"\n\n🧠 Room Mood: {sentiment}"

    return result

def get_sentiment(messages):
    positive_words = ["good", "great", "nice", "happy", "love", "awesome", "cool"]
    negative_words = ["bad", "sad", "angry", "hate", "worst", "issue", "problem"]

    score = 0

    for msg in messages:
        text = msg["message"].lower()

        for word in positive_words:
            if word in text:
                score += 1

        for word in negative_words:
            if word in text:
                score -= 1

    if score > 0:
        return "😊 Positive"
    elif score < 0:
        return "😞 Negative"
    else:
        return "😐 Neutral"
    
def get_sentiment_ml(messages):
    results = {"positive": 0, "negative": 0, "neutral": 0}

    for msg in messages:
        sentiment = predict_sentiment(msg["message"])
        results[sentiment] += 1

    final = max(results, key=results.get)

    if final == "positive":
        return "😊 Positive"
    elif final == "negative":
        return "😞 Negative"
    else:
        return "😐 Neutral"