FROM python:3.13
# FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

# RUN apt update
# RUN apt install -y git

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persist HF cache in a known location
ENV HF_HOME=/opt/hf-cache

# Preload HF models to avoid downloading them at runtime
RUN python -m app.scripts.preload_models

EXPOSE 8000 5678

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
