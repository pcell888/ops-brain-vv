FROM python:3.10.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --default-timeout=120 --retries 10 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn .

COPY src/ ./src/

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
