- Always ensure that there are only around 500-700 lines of code per any one file. If there is more than that then chances are it needs to be split up. Consult me when so.
- Ensure that `taster` is used for *anything* that might need to be integration tested. if you need to write a script to support a test, evaluate `taster` first, and either use that, or add a new command/argument. `taster` can be built with `flavor`, and `taster` should be able to build itself as well.
- if `taster` does not work then `flavor` is broken.

# CRITICAL BUILD RULES - DO NOT VIOLATE
- **ALWAYS USE pip3 FOR WHEEL OPERATIONS** - NEVER use `pip` (without 3), NEVER use `uv pip` for wheel/download commands
- **ALWAYS USE flavor.utils.subprocess.run_command** - NEVER use subprocess.run directly, ALWAYS import and use run_command from flavor
- **DO NOT REMOVE COMMENTS ABOUT pip3** - Every run_command that uses pip3 MUST have a comment explaining why pip3 is critical