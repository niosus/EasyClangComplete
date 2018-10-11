# Get correct flags #
There are multiple options to configure the plugin in such a way that
everything works without major pain. This document outlines all these ways. It should answer all your questions

# Using CMake #

## This is the recommended method ##
EasyClangComplete can search for `CMakeLists.txt` and generate a
`compile_commands.json` file from it. See next
[section](#using-compile_commandsjson) for details on how this file is parsed.

To use `CMake` way of generating flags, make sure you set the `"flags_sources"`
in your settings. See how to set this setting correctly
[here](settings.md#flags_sources).

## Using catkin ##
For those using `catkin` (e.g. when developing with ROS) there is a special
step that needs to be taken. By default when running Sublime Text from GUI it
knows nothing about the paths set in `.bashrc` of your system. So we need to
manually update the `CMAKE_PREFIX_PATH` to be able to find `catkin`:

```json
"flags_sources": [
    {
      "file": "CMakeLists.txt",
      "prefix_paths": [ "/opt/ros/indigo",
                        "~/catkin_ws/devel",
                        "$project_base_path/catkin_ws/devel" ]
    },
]
```

# Using compile_commands.json #
This file defines the flags per target (read more about it
[here](https://clang.llvm.org/docs/JSONCompilationDatabase.html)). When this
file is found EasyClangComplete reads it and finds appropriate target given
the file which is currently opened by the user.

When not using `CMake` make sure you set the `"flags_sources"` in your settings
to look for the `compile_commands.json` file. See how to set this setting
correctly [here](settings.md#flags_sources).
