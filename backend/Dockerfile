# Base image
FROM python:3.9

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy all backend files
COPY --chown=user . /app

# Run FastAPI app
# Update backend.main:app according to your main FastAPI file
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
