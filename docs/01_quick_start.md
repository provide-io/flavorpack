# ##_ Quick Start: Your First Flavor Package

This guide will walk you through packaging a simple Python "Hello, World!" application with Flavor. By the end, you will have a single, executable file that you can run on any machine with the same architecture, without needing Python or any dependencies installed.

### Prerequisites

*   You have installed `flavor`. If not, follow the installation instructions.
*   You are in a terminal with the `flavor` environment activated (by running `source env.sh` from the root of the flavor project).

### Step 1: Create Your Application Structure

First, create a new directory for your application. We'll call it `my_awesome_app`. It's best to create this outside of the `flavor` project directory.

```bash
mkdir -p my_awesome_app/my_awesome_app
```

This command creates the main project folder and a sub-folder that will contain our Python source code.

### Step 2: Write Your Python Code

Now, let's create the Python application file. Create a file named `my_awesome_app/my_awesome_app/main.py` with the following content:

```python
# my_awesome_app/my_awesome_app/main.py

import sys

def hello():
    """Prints a greeting."""
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
        print(f"Hello, {name}!")
    else:
        print("Hello, World!")

if __name__ == "__main__":
    hello()
```

Next, create an `__init__.py` file to make it a proper Python package.

```bash
touch my_awesome_app/my_awesome_app/__init__.py
```

Your directory should now look like this:
```
my_awesome_app/
└── my_awesome_app/
    ├── __init__.py
    └── main.py
```

### Step 3: Create the Flavor Manifest

Flavor needs to know how to package your application. You do this by creating a `pyproject.toml` file in the root of your application directory (`my_awesome_app/`).

Create the file `my_awesome_app/pyproject.toml` with this content:

```toml
# my_awesome_app/pyproject.toml

[project]
name = "my_awesome_app"
version = "0.1.0"
authors = [
    { name="A. Developer", email="a.developer@example.com" },
]
description = "A simple 'Hello, World!' application."
requires-python = ">=3.11"

# This section tells Flavor how to package the application
[tool.flavor]
entry_point = "my_awesome_app.main:hello"
```

The `[tool.flavor]` section is the most important part.
*   `entry_point`: This tells Flavor what function to run when the executable is launched. It's in the format `package_name.module_name:function_name`.

### Step 4: Package Your Application

Now for the magic. Navigate into your application's root directory and run the `flavor package` command.

```bash
cd my_awesome_app
flavor package
```

You will see output as Flavor builds your application, finds the dependencies (in this case, none), and creates the package. When it's done, you will have a new file in your directory. The name will vary based on your OS and architecture, but it will look something like `my_awesome_app-0.1.0-linux-amd64`.

### Step 5: Run Your Packaged Application!

This new file is your self-contained application. You can run it directly.

```bash
# Run without arguments
./my_awesome_app-0.1.0-linux-amd64
```
**Output:**
```
Hello, World!
```

```bash
# Run with arguments
./my_awesome_app-0.1.0-linux-amd64 Jules The Engineer
```
**Output:**
```
Hello, Jules The Engineer!
```

Congratulations! You have successfully created a portable, single-file executable with Flavor. You can copy this one file to another machine (with the same OS/architecture) and it will run without needing to install Python or anything else.

---

**Now that you've seen how it works, let's dive deeper.**

➡️ **Next: [Core Concepts](./02_core_concepts.md)** - Understand the technology that makes this possible.
