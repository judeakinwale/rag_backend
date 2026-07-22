FROM python:3.13
# FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

# RUN apt update
# RUN apt install -y git

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 5678

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
