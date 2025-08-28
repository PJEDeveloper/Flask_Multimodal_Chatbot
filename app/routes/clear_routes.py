# Flask utilities for defining routes and sending JSON responses
from flask import Blueprint, jsonify # type: ignore   

# Importing standard library module for interacting with the operating system
import os

# Utility to free GPU memory
from app.services.cache_service import clear_gpu_cache  

# Utility to reset conversation state      
from app.utils.conversation_manager import reset_conversation 

# Import the global conversation object used to maintain the chat history across requests
from app.utils.conversation_manager import conversation


# Create a Flask Blueprint for clearing operations
clear_bp = Blueprint("clear", __name__)

@clear_bp.route("/clear", methods=["POST"])
def clear_conversation():
    """
    Clears the entire conversation history and GPU cache.
    Useful for resetting the system state.
    """
    reset_conversation()
    clear_gpu_cache()
    return jsonify({"message": "Conversation and cache cleared successfully."})

@clear_bp.route("/clear_text", methods=["POST"])
def clear_text():
    """
    Clears text input.    
    """
    return jsonify({"message": "Text input cleared."})

@clear_bp.route("/clear_audio_video", methods=["POST"])
def clear_audio_video():
    """
    Removes any temporary audio/video files from previous requests.
    Clears GPU cache if files were removed.
    """
    removed = False
    for file in ["temp_audio.wav", "temp_video.mp4"]:
        if os.path.exists(file):
            os.remove(file)
            removed = True
    if removed:
        clear_gpu_cache()
    return jsonify({"message": "Audio/Video cleared."})

@clear_bp.route("/clear_image", methods=["POST"])
def clear_image():
    """
    Removes any temporary image file if present.
    Clears GPU cache after removal.
    """
    if os.path.exists("temp_image.jpg"):
        os.remove("temp_image.jpg")
        clear_gpu_cache()
    return jsonify({"message": "Image cleared."})

@clear_bp.route("/clear_document", methods=["POST"])
def clear_document():
    """
    Clears document-related context from conversation.
    """
    global conversation
    
    conversation[:] = [
        msg for msg in conversation
        if "[Document Context]" not in msg.get("content", "") and not (msg["role"] == "assistant" and not msg["content"].strip())
    ]

    return jsonify({"message": "Document context cleared."})