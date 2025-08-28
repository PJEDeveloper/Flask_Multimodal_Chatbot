# Import PyTorch for model loading and tensor operations
import torch

# Import Hugging Face components for model, tokenizer, and inference pipeline
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers.pipelines import pipeline

# Import configuration for quantization (BitsAndBytes)
from transformers.utils.quantization_config import BitsAndBytesConfig

# Import project-specific configuration and logger
from config import config, logger

# Import standard libraries for timing and regular expressions
import time

# Import regular expressions module for pattern matching and text processing
import re

# Import sentence splitter utility for text processing
from sentence_splitter import SentenceSplitter

# Sentence splitter for post-processing
splitter = SentenceSplitter(language='en')

# Globals for pipeline and tokenizer
mistral_pipeline = None
mistral_tokenizer = None

# Function to load the Mistral model in 4-bit precision with BitsAndBytes configuration
def load_mistral():
    global mistral_pipeline, mistral_tokenizer

    # Load the model and tokenizer only if the pipeline is not already initialized
    if mistral_pipeline is None:
        print("Loading Mistral model in 4-bit mode...")

        # Configure BitsAndBytes for 4-bit quantization with NF4 and FP16 computation
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        # Load the Mistral model with quantization, automatic device mapping, and offloading
        mistral_model = AutoModelForCausalLM.from_pretrained(
            config.MODEL_PATH,
            device_map="auto",
            quantization_config=bnb_config,
            torch_dtype=torch.float16,
            offload_folder=config.OFFLOAD_FOLDER,
            offload_state_dict=True
        )

        # Ensure proper padding by aligning pad token with EOS token
        mistral_model.config.pad_token_id = mistral_model.config.eos_token_id

        # Load tokenizer for the Mistral model
        mistral_tokenizer = AutoTokenizer.from_pretrained(config.MODEL_PATH)

        # Create a text-generation pipeline using the loaded model and tokenizer
        mistral_pipeline = pipeline(
            "text-generation",
            model=mistral_model,
            tokenizer=mistral_tokenizer
        )

    # Return initialized pipeline and tokenizer
    return mistral_pipeline, mistral_tokenizer

# Function to remove bracketed tags and extra spaces from a response string
def clean_response_text(text: str) -> str:
    # Remove any text enclosed in brackets followed by a colon (e.g., [Tag]:)
    text = re.sub(r'\[.*?\]:\s*', '', text)
    # Trim leading and trailing whitespace and return the cleaned text
    return text.strip()

# Function to normalize line breaks in text for proper Markdown rendering
def format_response_for_markdown(text: str) -> str:
    # Replace Windows-style line breaks with standard Unix line breaks
    text = text.replace('\r\n', '\n')

    # Detect if text contains multiple numbered lines (e.g., a list or steps)
    numbered_lines = re.findall(r'^\d+\s*$', text, flags=re.M)
    if len(numbered_lines) >= 3:
        # Add bold formatting to numbered list items and restructure for readability
        text = re.sub(r'(\d+)\s*\n\s*([A-Z][^\n:]+):', r'\1. **\2:**', text)
        text = re.sub(r'(\d+)(?!\.)\s', r'\1. ', text)
        text = re.sub(r'(\d+\.\s\*\*.*?)(?=\d+\.\s|\Z)',
                      lambda m: re.sub(r'\n+', ' ', m.group(0)),
                      text, flags=re.S)
    else:
        # Normalize spacing for non-numbered text by collapsing multiple newlines and adding Markdown breaks
        text = re.sub(r'\n{2,}', '\n\n', text)
        text = re.sub(r'(?<!\n)\n(?!\n)', '  \n', text)

    # If code-like patterns are detected, wrap the text in Markdown code block syntax
    if re.search(r'(^|\n)(def |class |import |print\(|for |while )', text):
        if not re.search(r'```', text):
            text = f"```python\n{text}\n```"

    # Return the fully formatted text without leading or trailing whitespace
    return text.strip()

# Function to validate and correct roles in a conversation to maintain proper structure
def fix_conversation_roles(conversation):
    fixed_conversation = []
    last_role = None

    # Iterate through all messages and enforce correct role ordering
    for msg in conversation:
        role = msg.get("role")
        content = msg.get("content", "").strip()

        # Skip invalid roles and log a warning
        if role not in ["system", "user", "assistant"]:
            logger.warning(f"Invalid role found and skipped: {role}")
            continue

        # Insert missing assistant responses if two consecutive user messages occur
        # Skip duplicate assistant messages to avoid redundancy
        if last_role == role and role != "system":
            if role == "user":
                fixed_conversation.append({"role": "assistant", "content": ""})
            elif role == "assistant":
                logger.warning("Skipping duplicate assistant role")
                continue

        # Add the current message to the corrected conversation list
        fixed_conversation.append({"role": role, "content": content})
        last_role = role

    # Ensure the conversation does not end with a user message without an assistant reply
    if fixed_conversation and fixed_conversation[-1]["role"] == "user":
        fixed_conversation.append({"role": "assistant", "content": ""})

    # Return the validated and corrected conversation
    return fixed_conversation

# Function to generate a response from the Mistral model using a validated conversation history
def generate_response(conversation, max_tokens=8192):
    try:
        # Ensure conversation roles are valid and properly structured
        conversation = fix_conversation_roles(conversation)

        # Load the quantized Mistral pipeline and tokenizer
        mistral_pipe, tokenizer = load_mistral()
        assert tokenizer is not None, "Tokenizer not loaded."

        # Format the conversation into a chat template for the model
        formatted_prompt = tokenizer.apply_chat_template(
            conversation, tokenize=False, add_generation_prompt=True
        )

        # Generate a response from the model and measure the time taken
        start_time = time.time()
        response = mistral_pipe(
            formatted_prompt,
            max_new_tokens=max_tokens,
            return_full_text=False,
            temperature=0.3,
            do_sample=True
        )
        elapsed = time.time() - start_time
        logger.info(f"Response generated in {elapsed:.2f}s")

        # Clean raw output text and prepare it for Markdown display
        raw_text = response[0]["generated_text"]
        cleaned_text = clean_response_text(raw_text)
        final_text = format_response_for_markdown(cleaned_text)

        # Return the processed response text
        return final_text

    # Log and raise an error if response generation fails
    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        raise RuntimeError("Failed to generate response")
