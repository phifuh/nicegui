FROM python:3.13-slim
WORKDIR /app
COPY . .
ENV POETRY_DYNAMIC_VERSIONING_BYPASS=0.0.0
RUN pip install --no-cache-dir .
EXPOSE 8080
CMD ["python", "demo.py"]
