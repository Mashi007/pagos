FROM python:3.12-slim 
WORKDIR /app 
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt 
COPY . . 
ENV PORT=8080 
ENV PYTHONUNBUFFERED=1 
CMD ["sh", "-c", "gunicorn main:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --timeout 120"]
