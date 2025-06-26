FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear la carpeta uploads si no existe
RUN mkdir -p static/uploads

CMD ["gunicorn", "--bind", "0.0.0.0:${PORT}", "app_web:app"]
