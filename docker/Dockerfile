FROM python:3.12-slim

WORKDIR /app

# Create a non-root user
RUN useradd --create-home --shell /bin/bash idsuser

COPY py/ /app/py/

RUN chown -R idsuser:idsuser /app

USER idsuser

CMD ["python", "py/response.py"]
