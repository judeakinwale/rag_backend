FROM python:3.13
# FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN apt update

# RUN apt install -y git
RUN apt install -y \
  libgl1 \
  libglib2.0-0 \
  libsm6 \
  libxext6 \
  libxrender1

RUN pip install --no-cache-dir -r requirements.txt

# Persist HF cache in a known location
ENV HF_HOME=/opt/hf-cache

COPY ./app/scripts/preload_models.py ./app/scripts/preload_models.py

# Preload HF models to avoid downloading them at runtime
RUN python -m app.scripts.preload_models

COPY . .

RUN pip install --no-cache-dir git+https://github.com/judeakinwale/rag_packages.git@main

EXPOSE 8000 5678

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
