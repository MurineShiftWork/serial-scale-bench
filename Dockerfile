FROM python:3.12-slim

WORKDIR /app

# Install the package from its own pyproject (no requirements.txt in this project).
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

# Console entry point (see [project.scripts]); compose overrides with --device etc.
CMD ["serial-scale-bench"]
