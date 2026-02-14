FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0
RUN pip install --no-cache-dir ".[y-py]"
EXPOSE 8080
CMD ["python", "demo.py"]
