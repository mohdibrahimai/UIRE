FROM python:3.11-slim
WORKDIR /app
COPY ./uire /app/uire
COPY ./uire/ops/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
EXPOSE 8000
CMD ["uvicorn","uire.api.main:app","--host","0.0.0.0","--port","8000"]
