# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the working directory contents into the container
COPY . .

# Set environment variables
ENV FLASK_APP=flaskr/__init__.py
ENV FLASK_RUN_HOST=0.0.0.0

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["flask", "run"]
