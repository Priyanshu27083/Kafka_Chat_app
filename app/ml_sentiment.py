from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# 🔥 Training data (you can expand later)
texts = [
    "I love this", "this is great", "awesome work", "very good", "cool app",
    "I hate this", "this is bad", "worst experience", "very angry", "problem here",
    "okay", "fine", "normal", "nothing special", "it works"
]

labels = [
    "positive", "positive", "positive", "positive", "positive",
    "negative", "negative", "negative", "negative", "negative",
    "neutral", "neutral", "neutral", "neutral", "neutral"
]

# 🔥 Train model
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(texts)

model = MultinomialNB()
model.fit(X, labels)


def predict_sentiment(text):
    X_test = vectorizer.transform([text])
    return model.predict(X_test)[0]