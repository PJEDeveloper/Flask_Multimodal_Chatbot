# PyTorch library for tensor operations and GPU acceleration
import torch

# PIL (Python Imaging Library) for opening and manipulating image files
from PIL import Image

# Hugging Face Transformers components for BLIP:
# BlipProcessor: Handles preprocessing of images (resizing, normalization) and tokenization.
# BlipForConditionalGeneration: The BLIP model used for generating captions from images.
from transformers import BlipProcessor, BlipForConditionalGeneration

# Custom utility for clearing GPU cache after inference to prevent VRAM overflow
from app.services.cache_service import clear_gpu_cache

# Python's standard logging module for tracking events and debugging
import logging

# Type hints for better code clarity and static type checking:
# Tuple: For specifying function return types with multiple values.
# Optional: For variables or arguments that can be None or a specific type.
from typing import Tuple, Optional


# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global variables to store BLIP processor and model
# Optional typing allows them to start as None and be initialized later (enable lazy loading)
blip_processor: Optional[BlipProcessor] = None
blip_model: Optional[BlipForConditionalGeneration] = None

def load_blip() -> Tuple[BlipProcessor, BlipForConditionalGeneration]:
    """
    Loads the BLIP image captioning model and processor if not already loaded.
    Uses lazy loading to avoid unnecessary memory usage until needed.
    
    Returns:
        Tuple containing (BlipProcessor, BlipForConditionalGeneration) for captioning tasks.
    """
    global blip_processor, blip_model

    # Only load if not already initialized (saves load time and GPU memory on repeated calls)
    if blip_model is None or blip_processor is None:
        logger.info("Loading BLIP model for image captioning...")

        # Load processor for preparing images into model-compatible format
        blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-large")  # type: ignore

        # Load BLIP model with optimized settings:
        # Half precision (float16) for reduced memory usage
        # device_map="auto" lets Hugging Face automatically distribute layers across available devices (e.g., GPU)
        blip_model = BlipForConditionalGeneration.from_pretrained(
            "Salesforce/blip-image-captioning-large",
            torch_dtype=torch.float16,
            device_map="auto"
        )
        logger.info("BLIP model loaded successfully.")

    # Ensure both processor and model are ready before returning
    assert blip_processor is not None
    assert blip_model is not None
    return blip_processor, blip_model

def process_image(image_path: str) -> str:
    """
    Generates a descriptive caption for the given image using BLIP.
    
    Steps:
    1. Load BLIP processor and model (lazy loading if not already initialized).
    2. Open the image, convert to RGB (ensures consistency for processing).
    3. Preprocess the image into tensors for BLIP input.
    4. Generate caption using the model.
    5. Decode model output to a human-readable string.
    6. Clear GPU cache to free memory for next operations.
    
    Args:
        image_path (str): Path to the image file to caption.
    
    Returns:
        str: Generated image caption.
    """
    logger.info(f"Processing image: {image_path}")
    processor, model = load_blip()

    # Open the image and ensure it's in RGB format (avoids mode issues like RGBA or grayscale)
    logger.info("Opening and converting image to RGB...")
    raw_image = Image.open(image_path).convert("RGB")

    # Prepare image for model inference
    logger.info("Preparing inputs for BLIP model...")
    inputs = processor(raw_image, return_tensors="pt")

    # Move inputs to the same device as the model and use float16 for efficiency
    inputs = {k: v.to(model.device, dtype=torch.float16) for k, v in inputs.items()}

    # Generate caption using BLIP model
    logger.info("Generating caption using BLIP model...")
    output = model.generate(**inputs)

    # Decode token IDs to text using processor's tokenizer
    caption = processor.tokenizer.decode(output[0], skip_special_tokens=True)  # type: ignore[attr-defined]
    logger.info(f"Generated caption: {caption}")

    # Free up GPU memory to prevent memory leaks in long-running apps
    clear_gpu_cache()
    logger.info("Cleared GPU cache after caption generation.")

    return caption