from pymongo import MongoClient
import time

# connect to MongoDB (local)
client = MongoClient("mongodb://localhost:27017/")

# database
db = client["kafka_chat"]

# collection
messages_collection = db["messages"]


# 🔹 Save message
def save_message(room, username, message, timestamp):
    messages_collection.insert_one({
        "room": room,
        "username": username,
        "message": message,
        "timestamp": timestamp
    })


# 🔹 Load messages for a room
def load_messages(room):
    return list(messages_collection.find(
        {"room": room}
    ).sort("timestamp", 1))