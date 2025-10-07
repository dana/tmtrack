# Use a relevant Ubuntu base
FROM ubuntu:24.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# Install dependencies
RUN apt-get update && \
    apt-get install -y python3-pip python3-dev build-essential curl telnet lsof vim net-tools netcat-openbsd python3.12-venv

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["uwsgi", "--ini", "uwsgi.ini"]
