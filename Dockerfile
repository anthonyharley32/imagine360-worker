# Imagine360 Serverless Worker for RunPod
# Converts perspective video to 360° equirectangular panoramic video

FROM runpod/base:0.6.2-cuda12.2.0

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Clone Imagine360
RUN git clone https://github.com/3DTopia/Imagine360.git

# Install dependencies
WORKDIR /app/Imagine360
RUN pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121 && \
    pip install xformers==0.0.22.post7 && \
    pip install -r requirements.txt && \
    python -m pip install -e "git+https://github.com/cvg/GeoCalib#egg=geocalib"

# Install gdown for Google Drive model downloads
RUN pip install gdown

# Download model checkpoints from Google Drive at build time
# NOTE: These are large files. If the Google Drive link requires manual approval,
# you may need to download them manually and COPY them into the image instead.
RUN mkdir -p /app/models/imagine360 && \
    gdown --folder "https://drive.google.com/drive/folders/1kjuZqJz8ZDkhUi9tb7AIsc9JlQPRK97Z" -O /app/models/imagine360 || \
    echo "WARNING: Google Drive download may have failed. Models may need manual download."

# Download SAM ViT-B checkpoint
RUN mkdir -p /app/models/sam && \
    wget -q "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth" -O /app/models/sam/sam_vit_b_01ec64.pth

# Copy handler
WORKDIR /app
COPY handler.py /app/handler.py

# Install runpod SDK
RUN pip install runpod

CMD ["python", "/app/handler.py"]
