# ##_ PSPF/2025 Specification Reference

This document provides a developer-focused reference for the Progressive Secure Package Format (PSPF). It is a companion to the other guides, intended for advanced users who need to fine-tune their package's behavior by directly manipulating the metadata generated from their `pyproject.toml`.

While the `flavor` tool abstracts away most of this complexity, understanding the underlying metadata structure is key to unlocking Flavor's full potential.

## Metadata (`metadata.json`)

This is the instruction manual for the package launcher. Here is a breakdown of the main sections and their keys.

### `package` Object

Basic information about your package.

| Key       | Type   | Description                               |
| :-------- | :----- | :---------------------------------------- |
| `name`    | string | The name of your package.                 |
| `version` | string | The package version (should follow SemVer). |

---

### `slots` Array

An array of objects, where each object describes a "slot" or chunk of data in the package.

| Key          | Type   | Description                                                                                             |
| :----------- | :----- | :------------------------------------------------------------------------------------------------------ |
| `name`       | string | A unique name for the slot.                                                                             |
| `purpose`    | string | The semantic type of the content (see "Slot Purposes" below).                                           |
| `lifecycle`  | string | How the launcher should handle the slot's data (see "Slot Lifecycles" below).                             |
| `extract_to` | string | Optional. The relative path where the file should be placed in the runtime environment.                   |
| `platform`   | string | Optional. Platform identifier (e.g., "linux-amd64") if this slot is platform-specific.                    |
| `checksum`   | string | The checksum of the slot's data, for integrity checks.                                                  |
| `size`       | number | The size of the slot's data in bytes.                                                                   |

---

### `execution` Object

Defines how to run the application.

| Key            | Type   | Description                                                                                  |
| :------------- | :----- | :------------------------------------------------------------------------------------------- |
| `primary_slot` | number | The index of the main executable slot to be run. (Handled automatically for Python apps).      |
| `command`      | string | The command to execute. Can use placeholders like `{workenv}`.                               |
| `env`          | object | A key-value map of environment variables to set specifically for the application's execution. |

---

### `workenv` Object

Defines the isolated work environment that the application runs in.

| Key           | Type    | Description                                                                                              |
| :------------ | :------ | :------------------------------------------------------------------------------------------------------- |
| `directories` | array   | A list of objects, each defining a directory to create (e.g., `{ "path": "tmp", "mode": "0700" }`).       |
| `env`         | object  | A key-value map of environment variables to set for the entire work environment (e.g., `TMPDIR`).        |

---

### `runtime` Object

Defines rules for the environment variables passed to the application. This provides a security layer.

| Key     | Type   | Description                                                                    |
| :------ | :----- | :----------------------------------------------------------------------------- |
| `set`   | object | A key-value map of variables to set, overriding any existing values.           |
| `unset` | array  | A list of variable names to remove from the environment.                       |
| `pass`  | array  | A list of variable names to allow through from the parent environment.         |
| `map`   | object | A key-value map to rename environment variables (e.g., `{ "OLD_NAME": "NEW_NAME" }`). |

---

## Slot Purposes

The `purpose` field in a slot object describes its content.

| Purpose     | Description                                                              |
| :---------- | :----------------------------------------------------------------------- |
| `payload`   | The main application data or code.                                       |
| `runtime`   | An executable runtime (e.g., the Python interpreter).                    |
| `config`    | A configuration file.                                                    |
| `asset`     | A static resource like an image, font, or data file.                     |
| `library`   | A shared library or dependency.                                          |
| `binary`    | A native executable binary that might be called by the application.      |
| `installer` | Files used for installation (e.g., Python wheels), often volatile.       |
| `data`      | Generic data files.                                                      |

---

## Slot Lifecycles

The `lifecycle` field in a slot object tells the launcher how to manage the slot's data.

| Lifecycle | Description                                                                |
| :-------- | :------------------------------------------------------------------------- |
| `runtime` | **(Default)** Available for the entire application execution.              |
| `volatile`| Deleted immediately after the setup phase is complete. Useful for installers. |
| `temp`    | Deleted after the current application session ends.                        |
| `cache`   | Kept for performance but can be regenerated if missing.                    |
| `init`    | Used only on the very first run, then removed.                             |
| `lazy`    | Loaded on-demand instead of being extracted initially.                     |
| `eager`   | Loaded immediately on startup.                                             |

---

**This reference covers the most common parts of the specification you might interact with. For a guide on how to contribute to Flavor itself, see the next section.**

➡️ **Next: [Contribution Guide](./06_contribution_guide.md)**
