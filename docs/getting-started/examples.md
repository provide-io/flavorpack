# Examples

Explore complete, working examples of FlavorPack in action. Each example includes full source code and step-by-step instructions.

## Quick Examples

### Minimal Package

The simplest possible FlavorPack package:

```python
# hello.py
print("Hello from FlavorPack!")
```

```toml
# pyproject.toml
[project]
name = "hello"
version = "1.0.0"

[tool.flavor]
entry_point = "hello"
```

```bash
flavor pack --manifest pyproject.toml --output hello.psp
./hello.psp  # Outputs: Hello from FlavorPack!
```

### CLI with Arguments

Handle command-line arguments:

```python
# greet.py
import sys

def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "World"
    print(f"Hello, {name}!")

if __name__ == "__main__":
    main()
```

```bash
flavor pack --manifest pyproject.toml --output greet.psp
./greet.psp Alice  # Outputs: Hello, Alice!
```

## Complete Applications

### 1. Task Manager CLI

A full-featured task management application:

=== "tasks.py"
    ```python
    #!/usr/bin/env python3
    """Simple task manager CLI."""
    
    import json
    import sys
    from datetime import datetime
    from pathlib import Path
    from typing import List, Dict, Optional
    
    class TaskManager:
        def __init__(self):
            self.tasks_file = Path.home() / ".tasks.json"
            self.tasks = self.load_tasks()
        
        def load_tasks(self) -> List[Dict]:
            """Load tasks from file."""
            if self.tasks_file.exists():
                with open(self.tasks_file) as f:
                    return json.load(f)
            return []
        
        def save_tasks(self):
            """Save tasks to file."""
            with open(self.tasks_file, 'w') as f:
                json.dump(self.tasks, f, indent=2)
        
        def add(self, description: str) -> None:
            """Add a new task."""
            task = {
                "id": len(self.tasks) + 1,
                "description": description,
                "completed": False,
                "created": datetime.now().isoformat()
            }
            self.tasks.append(task)
            self.save_tasks()
            print(f"✅ Added task #{task['id']}: {description}")
        
        def list(self, all_tasks: bool = False) -> None:
            """List tasks."""
            if not self.tasks:
                print("📝 No tasks found. Add one with 'add'!")
                return
            
            print("\n📋 Your Tasks:\n" + "=" * 50)
            for task in self.tasks:
                if not all_tasks and task['completed']:
                    continue
                
                status = "✓" if task['completed'] else "○"
                print(f"{status} [{task['id']}] {task['description']}")
            print("=" * 50)
        
        def complete(self, task_id: int) -> None:
            """Mark a task as complete."""
            for task in self.tasks:
                if task['id'] == task_id:
                    task['completed'] = True
                    task['completed_at'] = datetime.now().isoformat()
                    self.save_tasks()
                    print(f"✅ Completed task #{task_id}")
                    return
            print(f"❌ Task #{task_id} not found")
        
        def delete(self, task_id: int) -> None:
            """Delete a task."""
            self.tasks = [t for t in self.tasks if t['id'] != task_id]
            self.save_tasks()
            print(f"🗑️  Deleted task #{task_id}")
    
    def main():
        """Main CLI interface."""
        manager = TaskManager()
        
        if len(sys.argv) < 2:
            print("Task Manager - Usage:")
            print("  add <description>  - Add a new task")
            print("  list              - List pending tasks")
            print("  list --all        - List all tasks")
            print("  done <id>         - Mark task as complete")
            print("  delete <id>       - Delete a task")
            sys.exit(1)
        
        command = sys.argv[1]
        
        if command == "add" and len(sys.argv) > 2:
            description = " ".join(sys.argv[2:])
            manager.add(description)
        elif command == "list":
            show_all = "--all" in sys.argv
            manager.list(show_all)
        elif command == "done" and len(sys.argv) > 2:
            manager.complete(int(sys.argv[2]))
        elif command == "delete" and len(sys.argv) > 2:
            manager.delete(int(sys.argv[2]))
        else:
            print(f"❌ Unknown command: {command}")
    
    if __name__ == "__main__":
        main()
    ```

=== "pyproject.toml"
    ```toml
    [project]
    name = "task-manager"
    version = "1.0.0"
    description = "Simple task management CLI"
    
    [tool.flavor]
    entry_point = "tasks:main"
    ```

=== "Usage"
    ```bash
    # Package the application
    flavor pack --manifest pyproject.toml --output tasks.psp
    
    # Use the task manager
    ./tasks.psp add "Write documentation"
    ./tasks.psp add "Review pull requests"
    ./tasks.psp list
    ./tasks.psp done 1
    ./tasks.psp list --all
    ```

### 2. Web API Server

A FastAPI web application packaged with FlavorPack:

=== "api.py"
    ```python
    #!/usr/bin/env python3
    """Simple REST API server."""
    
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from datetime import datetime
    from typing import List, Optional
    import uvicorn
    
    app = FastAPI(title="Task API", version="1.0.0")
    
    # In-memory storage (for demo)
    tasks = []
    
    class Task(BaseModel):
        id: Optional[int] = None
        title: str
        description: Optional[str] = None
        completed: bool = False
        created_at: Optional[datetime] = None
    
    @app.get("/")
    def root():
        return {
            "message": "Task API",
            "version": "1.0.0",
            "endpoints": ["/tasks", "/docs"]
        }
    
    @app.get("/tasks", response_model=List[Task])
    def get_tasks():
        """Get all tasks."""
        return tasks
    
    @app.post("/tasks", response_model=Task)
    def create_task(task: Task):
        """Create a new task."""
        task.id = len(tasks) + 1
        task.created_at = datetime.now()
        tasks.append(task)
        return task
    
    @app.get("/tasks/{task_id}", response_model=Task)
    def get_task(task_id: int):
        """Get a specific task."""
        for task in tasks:
            if task.id == task_id:
                return task
        raise HTTPException(status_code=404, detail="Task not found")
    
    @app.put("/tasks/{task_id}", response_model=Task)
    def update_task(task_id: int, updated: Task):
        """Update a task."""
        for i, task in enumerate(tasks):
            if task.id == task_id:
                updated.id = task_id
                updated.created_at = task.created_at
                tasks[i] = updated
                return updated
        raise HTTPException(status_code=404, detail="Task not found")
    
    @app.delete("/tasks/{task_id}")
    def delete_task(task_id: int):
        """Delete a task."""
        global tasks
        tasks = [t for t in tasks if t.id != task_id]
        return {"message": f"Task {task_id} deleted"}
    
    def main():
        """Run the API server."""
        print("🚀 Starting Task API server...")
        print("📖 Documentation: http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    
    if __name__ == "__main__":
        main()
    ```

=== "pyproject.toml"
    ```toml
    [project]
    name = "task-api"
    version = "1.0.0"
    dependencies = [
        "fastapi",
        "uvicorn",
        "pydantic"
    ]
    
    [tool.flavor]
    entry_point = "api:main"
    ```

=== "Usage"
    ```bash
    # Package the API
    flavor pack --manifest pyproject.toml --output api.psp
    
    # Run the server
    ./api.psp
    
    # In another terminal, test the API
    curl http://localhost:8000/
    curl -X POST http://localhost:8000/tasks \
      -H "Content-Type: application/json" \
      -d '{"title": "Test task"}'
    ```

### 3. Data Processing Script

Process CSV files with pandas:

=== "process.py"
    ```python
    #!/usr/bin/env python3
    """CSV data processor with pandas."""
    
    import sys
    import pandas as pd
    from pathlib import Path
    
    def process_csv(input_file: str, output_file: str = None):
        """Process a CSV file."""
        
        # Read CSV
        print(f"📊 Reading {input_file}...")
        df = pd.read_csv(input_file)
        
        # Display info
        print(f"\nDataset Info:")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Columns: {', '.join(df.columns)}")
        
        # Basic statistics
        print(f"\n📈 Statistics:")
        print(df.describe())
        
        # Data cleaning
        print(f"\n🧹 Cleaning data...")
        df = df.dropna()  # Remove missing values
        df = df.drop_duplicates()  # Remove duplicates
        
        print(f"  Cleaned rows: {len(df)}")
        
        # Save processed data
        if output_file:
            df.to_csv(output_file, index=False)
            print(f"\n✅ Saved to {output_file}")
        
        return df
    
    def main():
        """Main entry point."""
        if len(sys.argv) < 2:
            print("Usage: process <input.csv> [output.csv]")
            sys.exit(1)
        
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        if not Path(input_file).exists():
            print(f"❌ File not found: {input_file}")
            sys.exit(1)
        
        process_csv(input_file, output_file)
    
    if __name__ == "__main__":
        main()
    ```

=== "pyproject.toml"
    ```toml
    [project]
    name = "csv-processor"
    version = "1.0.0"
    dependencies = [
        "pandas",
        "numpy"
    ]
    
    [tool.flavor]
    entry_point = "process:main"
    ```

=== "Usage"
    ```bash
    # Package the processor
    flavor pack --manifest pyproject.toml --output process.psp
    
    # Process a CSV file
    ./process.psp data.csv cleaned.csv
    ```

## Platform-Specific Examples

### macOS Menu Bar App

=== "Python Code"
    ```python
    # menubar.py
    import rumps
    
    class MenuBarApp(rumps.App):
        def __init__(self):
            super(MenuBarApp, self).__init__("🌶️")
            self.menu = ["Status", "Refresh", None, "Settings"]
        
        @rumps.clicked("Status")
        def status(self, _):
            rumps.notification(
                "FlavorPack Status",
                "Everything is working!",
                "Your app is running from a PSPF package"
            )
        
        @rumps.clicked("Refresh")
        def refresh(self, _):
            self.title = "🌶️✨"
            rumps.timer(2)(lambda _: setattr(self, 'title', '🌶️'))()
    
    if __name__ == "__main__":
        MenuBarApp().run()
    ```

### Windows System Tray

=== "Python Code"
    ```python
    # systray.py
    import pystray
    from PIL import Image, ImageDraw
    
    def create_image():
        # Create an icon
        image = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='orange')
        return image
    
    def on_quit(icon, item):
        icon.stop()
    
    def main():
        icon = pystray.Icon(
            "FlavorPack",
            create_image(),
            menu=pystray.Menu(
                pystray.MenuItem("Status", lambda: print("Running")),
                pystray.MenuItem("Quit", on_quit)
            )
        )
        icon.run()
    ```

### Linux Desktop Entry

=== "Desktop File"
    ```ini
    # flavorpack-app.desktop
    [Desktop Entry]
    Type=Application
    Name=FlavorPack App
    Comment=Packaged with FlavorPack
    Exec=/opt/flavorpack/myapp.psp
    Icon=flavorpack
    Terminal=false
    Categories=Utility;
    ```

## Integration Examples

### GitHub Actions

=== ".github/workflows/package.yml"
    ```yaml
    name: Package with FlavorPack
    
    on:
      release:
        types: [created]
    
    jobs:
      package:
        runs-on: ubuntu-latest
        
        steps:
        - uses: actions/checkout@v3
        
        - name: Setup Python
          uses: actions/setup-python@v4
          with:
            python-version: '3.11'
        
        - name: Install FlavorPack
          run: |
            git clone https://github.com/provide-io/flavorpack.git
            cd flavorpack
            uv sync
            make build-helpers
        
{% raw %}
        - name: Build Package
          run: |
            flavor pack \
              --manifest pyproject.toml \
              --output ${{ github.event.repository.name }}.psp

        - name: Upload Release Asset
          uses: actions/upload-release-asset@v1
          with:
            upload_url: ${{ github.event.release.upload_url }}
            asset_path: ./${{ github.event.repository.name }}.psp
            asset_name: ${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.psp
            asset_content_type: application/octet-stream
{% endraw %}
    ```

### Docker Multi-Stage Build

=== "Dockerfile"
    ```dockerfile
    # Build stage
    FROM python:3.11 AS builder

    # Install FlavorPack from source
    RUN git clone https://github.com/provide-io/flavorpack.git /flavorpack
    WORKDIR /flavorpack
    RUN pip install uv && uv sync && make build-helpers
    ENV PATH="/flavorpack/.venv/bin:$PATH"

    # Copy application
    WORKDIR /app
    COPY . .

    # Build package
    RUN flavor pack --manifest pyproject.toml --output app.psp
    
    # Runtime stage
    FROM ubuntu:22.04
    
    # Copy only the package
    COPY --from=builder /app/app.psp /usr/local/bin/app
    RUN chmod +x /usr/local/bin/app
    
    # Run the package
    CMD ["/usr/local/bin/app"]
    ```

## Testing Examples

### Unit Testing Packaged Apps

=== "test_package.py"
    ```python
    import subprocess
    import pytest
    
    def test_package_runs():
        """Test that package executes successfully."""
        result = subprocess.run(
            ["./myapp.psp", "--version"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "1.0.0" in result.stdout
    
    def test_package_verification():
        """Test package integrity."""
        result = subprocess.run(
            ["flavor", "verify", "myapp.psp"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "valid" in result.stdout.lower()
    ```

## More Examples

Explore our cookbook for more detailed examples:

- 📚 [CLI Tools](../cookbook/examples/cli-tool/) - Command-line applications
- 🌐 [Web Apps](../cookbook/examples/web-app/) - Flask, FastAPI, Django

