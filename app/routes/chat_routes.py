# Flask utilities for routing and synchronous responses
from flask import Blueprint, request, jsonify
import os

# Services for text generation, image, audio
from app.services.mistral_service import generate_response  
from app.services.blip_service import process_image
from app.services.whisper_service import process_audio

# Shared conversation
from app.utils.conversation_manager import conversation      

# Cache clearing
from app.services.cache_service import clear_gpu_cache

# Logger
from config import logger

# External services
from app.services.google_search_service import google_search
from app.services.document_service import extract_text_from_document

from werkzeug.utils import secure_filename

chat_bp = Blueprint("chat", __name__)

# Global document store
document_store = {"pages": [], "filename": "", "total_pages": 0, "file_path": ""}

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Upload Document Route
@chat_bp.route("/upload_document", methods=["POST"])
def upload_document():
    try:
        if "document" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        doc_file = request.files.get("document")
        if not doc_file or not getattr(doc_file, "filename", None):
            return jsonify({"error": "No valid file uploaded"}), 400

        filename = secure_filename(doc_file.filename or "uploaded_document")

        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, filename)
        doc_file.save(temp_path)
        

        extracted_text = extract_text_from_document(temp_path)

        if not extracted_text.strip():
            return jsonify({"error": "Document is empty or unreadable"}), 400

        pages = [extracted_text[i:i + 1000] for i in range(0, len(extracted_text), 1000)]

        document_store.update({
        "pages": pages,
        "filename": filename,
        "file_path": temp_path,
        "total_pages": len(pages)
        })

        return jsonify({
            "page": pages[0],
            "current_page": 1,
            "total_pages": len(pages)
        }), 200

    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        return jsonify({"error": f"Failed to process document: {str(e)}"}), 500



# Get Document Page
@chat_bp.route("/get_document_page", methods=["GET"])
def get_document_page():
    try:
        page_num = int(request.args.get("page", 1))

        # If in-memory pages are empty, reload from file
        if not document_store["pages"] and document_store["file_path"]:
            extracted_text = extract_text_from_document(document_store["file_path"])
            chunk_size = 2000  # or 3000 for fewer pages
            pages = [extracted_text[i:i + chunk_size] for i in range(0, len(extracted_text), chunk_size)]

            document_store["pages"] = pages
            document_store["total_pages"] = len(pages)

        if not document_store["pages"]:
            return jsonify({"error": "No document loaded"}), 400

        if page_num < 1 or page_num > document_store["total_pages"]:
            return jsonify({"error": "Invalid page number"}), 400

        return jsonify({
            "page": document_store["pages"][page_num - 1],
            "current_page": page_num,
            "total_pages": document_store["total_pages"]
        }), 200
    except Exception as e:
        logger.error(f"Error fetching page: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch page"}), 500


# Clear Document
@chat_bp.route("/clear_document", methods=["POST"])
def clear_document():
    global document_store
    removed_file = document_store.get("file_path")
    if removed_file and os.path.exists(removed_file):
        os.remove(removed_file)

    document_store = {"pages": [], "filename": "", "total_pages": 0, "file_path": ""}

    logger.info("Document context and temp file cleared.")
    return jsonify({"message": "Document cleared successfully."}), 200


@chat_bp.route("/stream", methods=["POST"])
def stream_response():
    logger.info("Received /stream POST request.")
    global conversation

    try:
        # Gather inputs
        user_input = request.form.get("text")
        audio_file = request.files.get("audio")
        image_file = request.files.get("image")
        google_search_enabled = request.form.get("google_search") == "true"
        document_interaction_enabled = request.form.get("document_interaction") == "true"
        document_context = request.form.get("document_context", "").strip()

        logger.info(f"User input: {user_input}, Google Search: {google_search_enabled}, Doc Enabled: {document_interaction_enabled}")

        response_text = ""
        search_results = []

        # Handle audio input
        if audio_file:
            audio_path = "temp_audio.wav"
            audio_file.save(audio_path)
            transcription = process_audio(audio_path)
            os.remove(audio_path)
            response_text += f"\n[Audio Transcription]: {transcription}"

        # Handle image input
        if image_file:
            img_path = "temp_image.jpg"
            image_file.save(img_path)
            caption = process_image(img_path)
            os.remove(img_path)
            response_text += f"\n[Image Description]: {caption}"

        # Limit document context for safety (optional upper bound)
        max_context_chars = 20000
        if len(document_context) > max_context_chars:
            document_context = document_context[:max_context_chars] + "...[truncated]"

        # Build combined user request
        if response_text:
            response_text += "\n\n"
        if user_input:
            response_text += f"User question: {user_input}\n"

        if document_interaction_enabled and document_context:
            response_text += f"\n[Document Context]\n{document_context}\nAnswer based on the document when relevant."

        if google_search_enabled and user_input:
            search_results = google_search(user_input)
            response_text += "\n[Internet Search Results]:\n" + "\n".join(map(str, search_results))

        if not response_text.strip():
            return jsonify({"error": "Invalid input: No content provided"}), 400

        # Add system message if missing
        if not any(msg["role"] == "system" for msg in conversation):
            conversation.insert(0, {"role": "system", "content": "You are an AI assistant."})

        # Append the new user message
        conversation.append({"role": "user", "content": response_text})

        # Filter out doc context if disabled
        effective_conversation = conversation.copy()
        if not document_interaction_enabled:
            effective_conversation = [msg for msg in effective_conversation if "[Document Context]" not in msg["content"]]

        # Ensure proper role alternation
        fixed_conversation = []
        last_role = None
        for msg in effective_conversation:
            if msg["role"] == "system" and not fixed_conversation:
                fixed_conversation.append(msg)
                continue
            if msg["role"] in ["user", "assistant"]:
                if last_role == msg["role"]:
                    continue  # skip consecutive duplicates
                fixed_conversation.append(msg)
                last_role = msg["role"]

        # Ensure it ends with a user prompt
        if not fixed_conversation or fixed_conversation[-1]["role"] != "user":
            fixed_conversation.append({"role": "user", "content": "Please continue."})

        # Generate model response
        model_response = generate_response(fixed_conversation)
        conversation.append({"role": "assistant", "content": model_response})

        # Cleanup GPU
        clear_gpu_cache()

        return jsonify({"response": model_response, "search_results": search_results}), 200

    except Exception as e:
        logger.error(f"Error during /stream processing: {e}", exc_info=True)
        return jsonify({"error": "Server error while processing request"}), 500