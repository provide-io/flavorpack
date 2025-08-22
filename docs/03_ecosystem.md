# ##_ The Flavor Ecosystem

Flavor is more than just a single command. It's a cross-language ecosystem of tools working together to build and run portable application packages. Understanding the different components will help you appreciate how Flavor achieves its goals of speed, security, and portability.

There are three main parts to the Flavor ecosystem:

1.  **The Python Orchestrator**: The `flavor` command-line tool you interact with.
2.  **The Native Builders**: High-performance tools (in Go and Rust) that assemble packages.
3.  **The Native Launchers**: The compact engines (in Go and Rust) embedded in every package.

```
            +---------------------------+
            |   You (The Developer)     |
            +-------------+-------------+
                          |
                          v
+-----------------------+-------------------------+
|  1. Python Orchestrator (`flavor` CLI)          |
|   - Parses your `pyproject.toml`                |
|   - Gathers dependencies & assets               |
|   - Generates the metadata.json                 |
|   - Invokes a Native Builder                    |
+-----------------------+-------------------------+
                          |
                          v
+-----------------------+-------------------------+
|  2. Native Builder (Go or Rust)                 |
|   - Assembles the final PSPF file               |
|   - Embeds a Native Launcher                    |
|   - Writes the index, metadata, and slots       |
|   - Signs the package                           |
+-----------------------+-------------------------+
                          |
                          v
+-----------------------+-------------------------+
|  Packaged Application (.psp file)               |
|                                                 |
|  +------------------+                           |
|  | 3. Native      |                           |
|  |    Launcher    | + Index + Metadata + Slots  |
|  +------------------+                           |
|                                                 |
+-------------------------------------------------+
```

### 1. The Python Orchestrator

When you run `flavor package`, you are using the Python orchestrator. This is the primary user-facing component of Flavor.

**Responsibilities:**
*   **User Interface:** Provides the `flavor` command-line interface (CLI).
*   **Project Analysis:** Reads and understands your `pyproject.toml` file.
*   **Dependency Management:** Resolves and vendors your application's dependencies (e.g., other Python packages).
*   **Manifest Generation:** Creates the `metadata.json` file that acts as the instruction manual for the launcher.
*   **Coordination:** Calls one of the native builders to perform the final, high-performance task of assembling the package.

The Python component is written to be flexible and to integrate deeply with the Python ecosystem, while offloading the performance-critical parts of package creation to the native helpers.

### 2. The Native Helpers (Go & Rust)

Flavor includes helper programs written in Go and Rust. These are pre-compiled binaries that the Python orchestrator calls to perform specialized tasks with high efficiency. Using these compiled languages for the heavy lifting makes Flavor fast and reduces runtime dependencies.

There are two types of helpers: **Builders** and **Launchers**.

#### Builders

The **Builder** is a command-line tool that the Python orchestrator calls to construct the final PSPF file.

**Responsibilities:**
*   Take the launcher binary, metadata, and all the data for the slots as input.
*   Lay out the file in the precise PSPF binary format.
*   Generate the cryptographic signature for the package.
*   Write the final, single-file executable to disk.

#### Launchers

The **Launcher** is the small, self-contained engine that is placed at the very beginning of every Flavor package. It is the first thing that runs when a user executes your packaged application.

**Responsibilities:**
*   Verify the package's integrity using the embedded signature and public key.
*   Create and manage the isolated runtime environment.
*   Handle progressive extraction and caching of slots.
*   Execute your application's entry point with the correct environment.

### Why Three Parts? Separation of Concerns

This multi-language, multi-component architecture is a deliberate design choice that gives Flavor several advantages:

*   **Flexibility (Python):** The user-facing tool is in Python, making it easy to integrate with Python's rich packaging ecosystem and simple to extend.
*   **Performance (Go/Rust):** The performance-critical tasks of building packages and the runtime operations of the launcher are handled by highly optimized, compiled code.
*   **Portability (Go/Rust):** The launchers have minimal dependencies, making the final packaged application extremely portable and self-contained.

By combining the strengths of these different languages, the Flavor ecosystem provides a user-friendly experience without sacrificing performance or security.

---

**With this understanding of the components, you're ready for more advanced topics.**

➡️ **Next: [Advanced Usage](./04_advanced_usage.md)**
