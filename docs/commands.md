# Available commands
There is a number of commands that you can run from Sublime Text with
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> (or
<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> on MacOS) that are related to
EasyClangComplete.

!!! tip "Pro tip"
    You can assign a key binding to any of the commands represented below to make running them quick and effortless.

## Clear CMake cache
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> -> `Clean current CMake cache`

This command makes sure we clean the temporary build folder where CMake
generates files.

## Show all errors
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> -> `Show all errors`

This command shows a panel with a list of all errors that are visible from the current translation unit. When you select one, the plugin will navigate you to the place where the error occurs.

## Show popup info
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> -> `Show popup info`

Show an information popup with the type of the symbol under the cursor.

## Open settings 
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> -> `Settings`

Open a new window with **Default** and **User** settings opened side by side for quick adjustment of the settings used by the plugin.

## Generate a compilation database with Bazel
<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> -> `Generate compile_commands.json`

Uses Bazel through the script provided by [@grailbio](https://github.com/grailbio/bazel-compilation-database) to generate a `compile_commands.json` file in the folder of your `WORKSPACE` file. By default, the plugin will then be able to read this file to get the correct flags.

