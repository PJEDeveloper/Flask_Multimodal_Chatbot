# Provides functions for interacting with the operating system (file paths, environment variables, etc.)
import os

# Provides functionality for application logging and message tracking
import logging

# Configuration class for application settings
class Config:
    # Path to the model, fetched from environment variable or defaults to a specific model
    MODEL_PATH = os.getenv("MODEL_PATH", "mistralai/Mistral-Nemo-Instruct-2407")
    
    # Device for computation (e.g., 'cuda' for GPU)
    DEVICE = "cuda"
    
    # Directory used for offloading large model parts if necessary
    OFFLOAD_FOLDER = "offload"
    
    # Maximum input text length allowed
    MAX_INPUT_LENGTH = 1000

# Create an instance of the configuration
config = Config()

# Set up a logger for the application
logger = logging.getLogger("ThinkerApp")