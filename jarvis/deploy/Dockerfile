# Jarvis AI Assistant - Production Dockerfile
# Optimized for GPU deployment with CSM and Whisper

FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    git \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create app user
RUN useradd -m -u 1000 jarvis
WORKDIR /app

# Copy requirements first for caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy CSM model files from parent
COPY models.py generator.py watermarking.py ./csm/

# Copy backend application
COPY backend/ ./backend/

# Set Python path
ENV PYTHONPATH=/app:/app/csm:/app/backend

# Create directories for models and data
RUN mkdir -p /app/models /app/data && chown -R jarvis:jarvis /app

# Switch to non-root user
USER jarvis

# Pre-download models (optional - uncomment to bake into image)
# RUN python -c "from generator import load_csm_1b; load_csm_1b(device='cpu')"
# RUN python -c "import whisper; whisper.load_model('large-v3')"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
