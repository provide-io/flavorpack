# Packaging a Web Application

Package FastAPI, Flask, or other web applications as self-contained executables.

## Example: FastAPI API Server

### Application Code

```python
# src/myapi/main.py
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="My API", version="1.0.0")

class Item(BaseModel):
    name: str
    price: float

@app.get("/")
def read_root():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/items")
def create_item(item: Item):
    return {"item": item, "message": "Created successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Configuration

```toml
# pyproject.toml
[project]
name = "myapi"
version = "1.0.0"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
]

[tool.flavor]
type = "python-app"
entry_point = "myapi.main:app"

[tool.flavor.execution]
command = "{workenv}/bin/uvicorn"
args = ["myapi.main:app", "--host", "0.0.0.0", "--port", "8000"]

[tool.flavor.execution.runtime.env]
pass = ["PORT", "HOST", "LOG_LEVEL"]
set = { "PYTHONUNBUFFERED" = "1" }
```

### Package and Deploy

```bash
# Package
flavor pack --output myapi.psp

# Run locally
./myapi.psp

# Run with custom port
PORT=3000 ./myapi.psp

# Deploy to server
scp myapi.psp user@server:/opt/myapi/
ssh user@server './opt/myapi/myapi.psp'
```

## Example: Flask Application

```python
# src/webapp/app.py
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['POST'])
def process_data():
    data = request.json
    # Process data
    return {"result": "processed"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

```toml
[tool.flavor]
type = "python-app"

[tool.flavor.execution]
command = "{workenv}/bin/python"
args = ["-m", "flask", "run", "--host=0.0.0.0"]

[[tool.flavor.slots]]
id = 2
path = "./templates"
extract_to = "templates"
lifecycle = "cached"
operations = "tar.gz"

[[tool.flavor.slots]]
id = 3
path = "./static"
extract_to = "static"
lifecycle = "cached"
operations = "tar.gz"
```

## Production Deployment

### With Systemd

```ini
# /etc/systemd/system/myapi.service
[Unit]
Description=My API Service
After=network.target

[Service]
Type=simple
User=apiuser
WorkingDirectory=/opt/myapi
ExecStart=/opt/myapi/myapi.psp
Restart=always
Environment="PORT=8000"
Environment="LOG_LEVEL=info"

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable myapi
sudo systemctl start myapi
```

### With Docker

```dockerfile
FROM alpine:latest
COPY myapi.psp /app/myapi.psp
RUN chmod +x /app/myapi.psp
EXPOSE 8000
CMD ["/app/myapi.psp"]
```

## See Also

- **[Docker Integration](../recipes/docker/)**
- **[CI/CD](../recipes/ci-cd/)**
- **[Multi-Platform Builds](../recipes/multi-platform/)**
