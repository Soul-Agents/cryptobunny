FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]
# Use Gunicorn for production
# CMD ["gunicorn", "run:app", "--bind", "0.0.0.0:8000", "--workers", "2"] 