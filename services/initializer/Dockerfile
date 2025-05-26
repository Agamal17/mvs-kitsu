FROM python:3.11
ENV PYTHONUNBUFFERED=1

WORKDIR /service
COPY pyproject.toml /service/pyproject.toml

RUN \
  pip install -U pip && \
  pip install poetry && \
  poetry config virtualenvs.create false && \
  poetry install --no-interaction --no-ansi

RUN poetry config virtualenvs.create false \
 && poetry install --no-interaction --no-ansi --no-root

COPY . /service

CMD ["python", "-m", "initializer"]

