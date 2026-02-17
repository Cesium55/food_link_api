FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .python-version uv.lock ./

RUN pip install uv

RUN uv sync --frozen

COPY src/ ./src/

# RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
# USER app

EXPOSE 8000

COPY run.py run_celery.py ./

CMD ["uv", "run", "python", "run.py"]
