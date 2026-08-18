FROM python:3.14.7-alpine3.23
WORKDIR /framework
COPY . .
RUN pip install uv && uv sync
ENTRYPOINT ["uv", "run", "pytest", "-s"]
