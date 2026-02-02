import torch
import sys

print(f"Python: {sys.version}")
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")
print(f"CUDA Version (Torch Build): {torch.version.cuda}")

if torch.cuda.is_available():
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
else:
    print("WARNING: CUDA is NOT available. You are running on CPU.")
    print("If you have an NVIDIA GPU, you likely installed the wrong PyTorch version.")
