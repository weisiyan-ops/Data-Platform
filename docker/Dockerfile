FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."

COPY . .

EXPOSE 8000

CMD ["onco-extract", "serve", "--port", "8000"]
