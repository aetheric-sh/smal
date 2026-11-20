# SMAL CLI and workspaces

## 1. Add one-shot command execution

- [ ] Keep cmd2 as the shared command implementation. Add a launcher that starts the REPL for `smal` and `smal repl`, and dispatches invocations such as `smal validate foo.smal` through the existing command pipeline.
- [ ] Provide launcher help and preserve cmd2's command-specific help. Pass shell arguments through without losing spaces, quotes, or literal special characters.
- [ ] Return a nonzero process status for parse errors and command failures, including handlers that report failure through `print_error()`. Keep the REPL banner, prompt, and startup messages out of one-shot output.
- [ ] Verify equivalent results for `validate` and `diagram` in both modes. Cover help, invalid commands, missing files, and paths containing spaces.

## 2. Discover workspaces and restore machines

- [ ] Define a `smal.toml` manifest with an optional `default_machine`, a list of `modules`, and an optional `default_module`.
- [ ] Find the nearest manifest by walking upward from the current directory. Add `--workspace PATH` for explicit selection and `--no-workspace` to disable discovery. Resolve manifest paths relative to the workspace root.
- [ ] Store the last active machine and module in user-local persistence, keyed by the resolved workspace root. Save changes after successful interactive selections.
- [ ] Restore the machine from disk at startup. Apply explicit selection first, then the last valid workspace selection, then the manifest default. A missing remembered file should fall back to the default.
- [ ] Verify discovery from nested directories, workspace isolation, stale paths, and one-shot commands that use the restored machine.

## 3. Restore workspace modules

- [ ] Use the manifest's module list for discovery and restore one active module through the existing module loader.
- [ ] Require per-workspace trust before automatically importing Python modules. Store trust in user-local persistence and give one-shot invocations a clear outcome without an interactive prompt.
- [ ] Restore the module before dispatching commands so its custom commands work in both modes. Apply the same explicit, remembered, and default precedence as machine selection.
- [ ] Verify trusted and untrusted startup, missing and invalid modules, and custom command dispatch. Document how to create a workspace, manage trust, and run commands in either mode.
