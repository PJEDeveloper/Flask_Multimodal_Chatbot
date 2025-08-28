# PyTorch library for deep learning and GPU operations
import torch  
# Python's built-in garbage collector to free unused CPU memory 
import gc    
# Logging module for tracking application events and debugging  
import logging 

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def clear_gpu_cache():
    """
    Clears GPU and CPU memory cache to free resources after model inference.    

    Steps:
    1. torch.cuda.empty_cache(): Releases unused cached memory on the GPU.
    2. gc.collect(): Runs Python's garbage collector to clear unreferenced objects in CPU RAM.
    3. torch.cuda.ipc_collect(): Cleans up inter-process communication (IPC) memory (useful in multi-GPU setups).
    """
    logger.info("Clearing GPU cache and triggering garbage collection...")

    # Clear PyTorch's CUDA cache (frees VRAM for future operations)
    torch.cuda.empty_cache()

    # Trigger Python garbage collection to release any CPU-side memory not in use
    gc.collect()

    # Clean up CUDA IPC memory blocks to avoid memory leaks in multi-process scenarios
    torch.cuda.ipc_collect()

    logger.info("GPU cache cleared successfully.")