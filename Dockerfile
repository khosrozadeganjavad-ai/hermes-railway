FROM python:3.11-slim
WORKDIR /app
COPY miniapp/server.py .
COPY miniapp/index.html .
EXPOSE 8080
CMD ["python3", "server.py"]
