FROM python:3.13.5-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 443

CMD ["gunicorn", "-c", "gunicorn_conf.py", "app:app"]
