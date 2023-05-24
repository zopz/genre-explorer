FROM python:3.11.3-slim-buster

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY src/ .

RUN adduser --disabled-password docker && \
    chown -R docker .

USER docker

CMD ["python", "main.py"]