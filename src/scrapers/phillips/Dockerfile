FROM apify/actor-python:3.11

# Copy requirements and install them
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY src/ ./src/

# Copy the entire project for shared utilities
COPY ../../src/ ./project_src/

# Set the working directory
WORKDIR /usr/src/app

# Run the actor
CMD ["python", "-m", "src.main"]