# ##_ Advanced Usage

You've packaged a simple application and understand the core concepts. Now, let's explore some of Flavor's more powerful features to handle real-world scenarios like managing dependencies, including data files, and customizing package behavior.

### Including Python Dependencies

Most Python applications have dependencies. Flavor handles these automatically.

Let's say your application needs the popular `requests` library. Simply add it to your `pyproject.toml` file under the `[project]` section's `dependencies` array.

```toml
# my_awesome_app/pyproject.toml

[project]
name = "my_awesome_app"
version = "0.2.0"
dependencies = [
    "requests>=2.28.0"
]
# ... other project settings

[tool.flavor]
entry_point = "my_awesome_app.main:hello"
```

When you run `flavor package`, the orchestrator will:
1.  Read the `dependencies` array.
2.  Download the `requests` package and its dependencies.
3.  Bundle them into one or more "slots" inside your final package.

Your application code can then `import requests` and use it, just as it would in a normal Python environment. Flavor ensures the library is available at runtime.

### Adding Data Files and Assets

What if your application needs to read a configuration file or display an image? You can package arbitrary files as **asset slots**.

You can define extra slots in your `pyproject.toml` under the `[tool.flavor]` section. Let's add a `config.json` file.

**1. Create the data file:**
Create a file named `config.json` in your project's root directory.
```json
{
    "greeting": "Hello from config!"
}
```

**2. Update your `pyproject.toml`:**
Add a `[[tool.flavor.slot]]` table to your manifest.

```toml
# my_awesome_app/pyproject.toml

[project]
# ...

[tool.flavor]
entry_point = "my_awesome_app.main:main"

# Define a new slot for our config file
[[tool.flavor.slot]]
name = "config_file"
source = "config.json"
purpose = "asset"
extract_to = "config.json"
```
*   `name`: A unique name for the slot.
*   `source`: The path to the file on your build machine.
*   `purpose`: We define this as an `asset`.
*   `extract_to`: The relative path where the file will be placed inside the package's runtime environment.

**3. Access the file in your code:**
Your application can now open and read this file from the path you specified in `extract_to`.

```python
# my_awesome_app/main.py
import json

def main():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print(config["greeting"])
    except FileNotFoundError:
        print("Could not find config.json!")

if __name__ == "__main__":
    main()
```

When you build and run this package, the launcher will extract `config.json` into the application's working directory, making it available to your script.

### Customizing Slot Lifecycles

By default, slots are available for the entire duration of your application's run. However, you can control their behavior with the `lifecycle` property.

For example, you might have a large asset that's only needed for a one-time setup. You can mark its lifecycle as `volatile`.

```toml
[[tool.flavor.slot]]
name = "one_time_data"
source = "setup_data.dat"
purpose = "data"
lifecycle = "volatile"
extract_to = "setup_data.dat"
```

A `volatile` slot will be **deleted automatically** after the application's setup phase is complete, saving disk space in the runtime cache. Other lifecycles include `cache` (can be regenerated if deleted) and `temp` (removed after the session ends).

### Choosing Your Launcher

Flavor comes with launchers written in both Go and Rust. By default, it will pick one for you. However, you can explicitly choose a launcher using the `--launcher-bin` flag.

```bash
# Explicitly use the Rust launcher
flavor package --launcher-bin /path/to/flavor-rs-launcher

# Explicitly use the Go launcher
flavor package --launcher-bin /path/to/flavor-go-launcher
```
You might do this for specific performance or security compliance reasons, as the different launchers may have slightly different characteristics.

---

**These advanced features give you fine-grained control over your packages. For the ultimate level of detail, you may need to consult the specification.**

➡️ **Next: [PSPF/2025 Specification Reference](./05_specification_reference.md)**
