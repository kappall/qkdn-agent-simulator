FROM python:3.14-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --upgrade pip setuptools wheel
RUN pip install .

ENV PYTHONUNBUFFERED=1

EXPOSE 8027 8028

CMD ["python", "-m", "main"]
