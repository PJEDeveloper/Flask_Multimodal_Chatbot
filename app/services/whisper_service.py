# PyTorch for model loading and GPU acceleration
import torch   

# Hugging Face classes for speech models and processing
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor  

# High-level interface for inference
from transformers.pipelines import pipeline  

# Custom utility to free GPU memory after use
from app.services.cache_service import clear_gpu_cache  

# For logging important events
import logging  

# For precise type annotations
from typing import Union, List, Dict, Any  

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Globals for lazy loading Whisper model components (avoid reloading on every call)
whisper_model = None
whisper_pipeline = None
whisper_processor = None

def load_whisper():
    """
    Loads the OpenAI Whisper model for automatic speech recognition (ASR).
    Uses lazy loading to reduce initial startup time and GPU memory usage.
    
    Steps:
    - Select the appropriate precision (float16 on GPU, float32 on CPU).
    - Load model, processor, and create an ASR pipeline.
    
    Returns:
        whisper_pipeline: Hugging Face pipeline for audio-to-text transcription.
    """
    global whisper_model, whisper_pipeline, whisper_processor

    # Load only once to optimize performance
    if whisper_pipeline is None:
        logger.info("Loading Whisper model for speech recognition...")

        # Pretrained Whisper model from Hugging Face
        model_id = "openai/whisper-large-v3-turbo"

        # Use float16 if CUDA is available for memory efficiency
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        logger.info(f"Using model_id={model_id}, torch_dtype={torch_dtype}")

        # Load model with reduced CPU memory usage and move to GPU
        whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True  # Minimizes RAM usage during load
        ).to("cuda")

        # Load processor (handles feature extraction + tokenization)
        whisper_processor = AutoProcessor.from_pretrained(model_id)

        # Create an ASR pipeline for easier inference
        whisper_pipeline = pipeline(
            "automatic-speech-recognition",          # Task type
            model=whisper_model,                     # Loaded model
            tokenizer=whisper_processor.tokenizer,   # Tokenizer for decoding outputs
            return_timestamps=True,                  # Include timestamps for each segment
            feature_extractor=whisper_processor.feature_extractor,  # Audio feature extractor
            torch_dtype=torch_dtype                  # Match computation precision
        )
        logger.info("Whisper pipeline loaded successfully.")

    # Return initialize Whisper pipeline
    return whisper_pipeline

def process_audio(file_path: str) -> str:
    """
    Transcribes an audio or video file into text using Whisper.
    
    Steps:
    1. Load Whisper pipeline (lazy load if not already initialized).
    2. Pass the file to the ASR pipeline for transcription.
    3. Merge text segments into a single string if multiple segments are returned.
    4. Clear GPU cache to free VRAM.
    
    Args:
        file_path (str): Path to the audio/video file.
    
    Returns:
        str: Full transcription text.
    """
    logger.info(f"Starting transcription for file: {file_path}")

    # Get Whisper pipeline (lazy-loaded)
    pipe = load_whisper()

    # Perform transcription with batch size = 1 (safe for long audio files)
    logger.info("Running Whisper pipeline for transcription...")
    result: Union[Dict[str, Any], List[Dict[str, Any]]] = pipe(file_path, batch_size=1)

    # If multiple segments are returned, combine them into a single transcript
    if isinstance(result, list):
        text = " ".join([seg.get("text", "") for seg in result])
    else:
        text = result.get("text", "")

    logger.info(f"Transcription completed. Length of text: {len(text)} characters")

    # Free GPU memory after processing
    clear_gpu_cache()
    logger.info("Cleared GPU cache after transcription.")

    # Return the final transcription text
    return text