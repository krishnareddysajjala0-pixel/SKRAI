# Use Python 3.10 as base
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick security policy to allow PDF/Text operations (required for moviepy)
RUN sed -i 's/pixel-limit" value="16GiB"/pixel-limit" value="32GiB"/' /etc/ImageMagick-*/policy.xml && \
    sed -i 's/domain="coder" rights="none" pattern="PDF"/domain="coder" rights="read|write" pattern="PDF"/' /etc/ImageMagick-*/policy.xml

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
