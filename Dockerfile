FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Change the working directory to the `app` directory
WORKDIR /app

# Copy the lockfile and `pyproject.toml` into the image
ADD uv.lock /app/uv.lock
ADD pyproject.toml /app/pyproject.toml

# Install dependencies
RUN uv sync --frozen --no-install-project

# Copy the project into the image
ADD . /app

# Sync the project
RUN uv sync --frozen

# Expose ports for MCP and OSC
EXPOSE 8080
EXPOSE 8000
EXPOSE 9000

# Run the Bitwig MCP Server
CMD ["python", "-m", "bitwig_mcp_server"]
