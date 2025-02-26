from flask import Flask, request, render_template, Response, jsonify
import time
import os
import torch
import re
import gc
from transformers import (
    pipeline,
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    BlipProcessor,
    BlipForConditionalGeneration,
    AutoModelForSpeechSeq2Seq,
    AutoProcessor,
)
from PIL import Image

app = Flask(__name__)

# Lazy initialization of models
mistral_pipeline = None
mistral_tokenizer = None
blip_processor = None
blip_model = None
whisper_model = None
whisper_pipeline = None
whisper_processor = None

# Global storage for processed media results
processed_audio_transcription = None
processed_video_transcription = None
processed_image_caption = None

conversation = [{"role": "system", "content": "You are a professional assistant, a subject matter expert, and a coding assitant."}]

def clear_gpu_cache():
    """Force clear GPU memory to prevent residual model states."""
    torch.cuda.empty_cache()
    gc.collect()
    torch.cuda.ipc_collect()

def load_models():
    """Initialize all models."""
    global mistral_pipeline, mistral_tokenizer, blip_processor, blip_model, whisper_model, whisper_pipeline, whisper_processor
    print("Loading Mistral-Nemo-Instruct-2407 with 8-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_skip_modules=["lm_head"],
        llm_int8_enable_fp32_cpu_offload=True,
    )
    mistral_model_name = "mistralai/Mistral-Nemo-Instruct-2407"
    mistral_model = AutoModelForCausalLM.from_pretrained(
        mistral_model_name,
        device_map="auto",
        quantization_config=bnb_config,
        torch_dtype=torch.float16,
        offload_folder="offload",
        offload_state_dict=True,
    )
    mistral_model.config.pad_token_id = mistral_model.config.eos_token_id
    mistral_tokenizer = AutoTokenizer.from_pretrained(mistral_model_name)
    mistral_pipeline = pipeline(
        "text-generation",
        model=mistral_model,
        tokenizer=mistral_tokenizer,
    )

    print('Clearin GPU Cache...')
    clear_gpu_cache()

    print("Loading BLIP-Image-Captioning-Large...")
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")
    blip_model = BlipForConditionalGeneration.from_pretrained(
        "Salesforce/blip-image-captioning-large",
        torch_dtype=torch.float16,
    ).to("cuda")

    print('Clearin GPU Cache...')
    clear_gpu_cache()

    print("Loading Whisper-Large-v3-Turbo...")
    model_id = "openai/whisper-large-v3-turbo"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
    )
    whisper_model.to("cuda")
    whisper_processor = AutoProcessor.from_pretrained(model_id)
    whisper_pipeline = pipeline(
        "automatic-speech-recognition",
        model=whisper_model,
        tokenizer=whisper_processor.tokenizer,
        return_timestamps=True,
        feature_extractor=whisper_processor.feature_extractor,
        torch_dtype=torch_dtype,
    )
    print("Models loaded successfully.")

    print('Clearin GPU Cache...')
    clear_gpu_cache()

def validate_input(input_text: str) -> bool:
    """Validate user input for length and complexity."""
    return bool(input_text and len(input_text.strip()) > 0 and len(input_text) <= 1000)

def determine_max_tokens(input_text: str) -> int:
    """Determine max_new_tokens based on input text length."""
    input_length = len(input_text.split())
    if input_length <= 10:
        return 512
    elif input_length <= 50:
        return 1024
    elif input_length <= 100:
        return 2048
    else:
        return 8192

@app.route("/", methods=["GET"])
def index():
    return render_template("index_stream.html")

@app.route("/clear", methods=["POST"])
def clear_conversation():
    """Clears previous inputs and conversation state."""
    global conversation
    conversation = [{"role": "system", "content": "You are a professional assistant, a subject matter expert, and a coding assitant."}]
    clear_gpu_cache()
    return jsonify({"message": "Conversation cleared successfully."})

@app.route("/clear_text", methods=["POST"])
def clear_text():
    """Clears only the text input but keeps uploaded files and conversation history."""
    return jsonify({"message": "Text input cleared."})

@app.route("/clear_audio_video", methods=["POST"])
def clear_audio_video():
    """Clears uploaded audio/video file from storage and session."""
    temp_audio = "temp_audio_input.wav"
    temp_video = "temp_video.mp4"
    
    removed = False
    if os.path.exists(temp_audio):
        os.remove(temp_audio)
        removed = True
    if os.path.exists(temp_video):
        os.remove(temp_video)
        removed = True

    if removed:
        clear_gpu_cache()

    return jsonify({"message": "Audio/Video cleared."})

@app.route("/clear_image", methods=["POST"])
def clear_image():
    """Clears uploaded image file from storage and session."""
    temp_image = "temp_image.jpg"
    
    if os.path.exists(temp_image):
        os.remove(temp_image)
        clear_gpu_cache()

    return jsonify({"message": "Image cleared."})

@app.route("/clear_media", methods=["POST"])
def clear_media():
    """Clears stored transcriptions and captions but keeps conversation history."""
    global processed_audio_transcription, processed_video_transcription, processed_image_caption
    processed_audio_transcription = None
    processed_video_transcription = None
    processed_image_caption = None
    return jsonify({"message": "Previous media cleared. You can upload new files now."})

def ensure_alternating_roles():
    """Ensure roles alternate between 'user' and 'assistant'."""
    global conversation
    filtered_conversation = [conversation[0]]

    for i in range(1, len(conversation)):
        if conversation[i]["role"] != conversation[i - 1]["role"]:
            filtered_conversation.append(conversation[i])

    conversation[:] = filtered_conversation

@app.route("/stream", methods=["POST"])
def stream_response():
    global conversation, mistral_tokenizer, processed_audio_transcription, processed_video_transcription, processed_image_caption

    user_input = request.form.get("text")
    audio_file = request.files.get("audio")
    image_file = request.files.get("image")
    video_file = request.files.get("video")

    response_text = None  # Ensure response_text is always initialized

    # Process Video (Only if new file is uploaded)
    if video_file:
        video_path = "temp_video.mp4"
        video_file.save(video_path)

        try:
            print("Processing video file...")
            result = whisper_pipeline(video_path, batch_size=1)
            processed_video_transcription = result["text"]  # Store result
            response_text = f"Video transcription:\n\"{processed_video_transcription}\""
            conversation.append({"role": "user", "content": response_text})
        except Exception as e:
            response_text = f"Error processing video: {e}"
        finally:
            os.remove(video_path)

        clear_gpu_cache()

    # Process Audio (Only if new file is uploaded)
    elif audio_file:
        audio_path = "temp_audio_input.wav"
        audio_file.save(audio_path)

        try:
            print("Processing audio file...")
            result = whisper_pipeline(audio_path, batch_size=1)
            processed_audio_transcription = result["text"]  # Store result
            response_text = processed_audio_transcription
            conversation.append({"role": "user", "content": processed_audio_transcription})
        except Exception as e:
            response_text = f"Error processing audio: {e}"
        finally:
            os.remove(audio_path)

        clear_gpu_cache()

    # Process Image (Only if new file is uploaded)
    elif image_file:
        image_path = "temp_image.jpg"
        image_file.save(image_path)

        try:
            raw_image = Image.open(image_path).convert("RGB")
            inputs = blip_processor(raw_image, return_tensors="pt").to("cuda", torch.float16)
            output = blip_model.generate(**inputs)
            processed_image_caption = blip_processor.decode(output[0], skip_special_tokens=True)  # Store result
            response_text = f"Image description: {processed_image_caption}"
            conversation.append({"role": "user", "content": response_text})
        except Exception as e:
            response_text = f"Error processing image: {e}"
        finally:
            os.remove(image_path)

        clear_gpu_cache()

    # If user input exists, combine it with media processing results
    elif user_input and validate_input(user_input):
        response_text = user_input

        # Constructing the user query to include media results
        context = ""
        if processed_audio_transcription:
            context += f"\n[Audio Transcription]: {processed_audio_transcription}"
        if processed_video_transcription:
            context += f"\n[Video Transcription]: {processed_video_transcription}"
        if processed_image_caption:
            context += f"\n[Image Description]: {processed_image_caption}"

        # Append the user query
        if user_input and validate_input(user_input):
            response_text = f"{context}\n\n[User]: {user_input}"
        else:
            response_text = f"{context}"

        # Ensure that the conversation log records this correctly
        conversation.append({"role": "user", "content": response_text})

    else:
        return Response("data: Invalid input.\n\n", content_type="text/event-stream")

    ensure_alternating_roles()

    # Add an empty assistant response if the last entry is from the user
    if conversation[-1]["role"] == "user":
        conversation.append({"role": "assistant", "content": ""})

    def clean_generated_text(text: str) -> str:
        """Ensures correct spacing between words, numbers, punctuation, and sentences."""
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)  # Add space between lowercase-uppercase
        text = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text)  # Space between letters and numbers
        text = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text)  # Space between numbers and letters
        text = re.sub(r"\s*([,!?])\s*", r"\1 ", text)  # Ensure space after punctuation (except periods)
        text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)  # Ensure space after sentence-ending punctuation
        text = re.sub(r"\s+", " ", text).strip()  # Normalize spaces
        return text
    
    def split_sentences(text: str) -> list:
        """Splits text into sentences properly, ensuring correct spacing."""
        return re.split(r'(?<=[.!?])\s+', text)  # Splits at sentence-ending punctuation with a space

    def generate_sync():
        try:
            if response_text:
                yield f"data: {response_text}\n\n"

            yield "data: \n\n///***Generating response... Please wait...\n\n"
            time.sleep(0.5)

            max_tokens = determine_max_tokens(response_text)

            # Format conversation using apply_chat_template
            formatted_prompt = mistral_tokenizer.apply_chat_template(
                conversation, tokenize=False, add_generation_prompt=True
            )

            response = mistral_pipeline(
                formatted_prompt,
                max_new_tokens=max_tokens,
                return_full_text=False,
                num_return_sequences=1,
                temperature=0.3,
                do_sample=True,
            )

            generated_text = response[0]["generated_text"]
            formatted_text = clean_generated_text(generated_text)
            conversation[-1]["content"] = formatted_text
            
            # Correctly split sentences using regex
            for sentence in split_sentences(formatted_text):
                yield f"\n\ndata: {sentence.strip()}\n\n"
                time.sleep(0.3)
            
            clear_gpu_cache()

        except Exception as e:
            yield f"data: Error generating response: {e}\n\n"
   
    return Response(generate_sync(), content_type="text/event-stream")

if __name__ == "__main__":
    load_models()
    app.run(host="0.0.0.0", port=5007, debug=True, use_reloader=False)
