# Geting correct compiler flags
There are multiple options to configure the plugin in such a way that
everything works without major pain. This document outlines all these ways.

!!! tip "Prefer CMake and Sublime Text projects"
    The preferred way is to use Sublime Text project to organize your code and to use CMake as your build system. This way the plugin should work out of the box. See details [below](#using-cmake-recommended).

## All flag sources <small>from settings and external</small>
There are three major sources for flags:

1. Flags defined in settings of ECC.
2. Flags generated from a flag source defined in `flags_sources`
   [settings](../settings/#flags_sources).
3. Flags generated from the compiler.

!!! tip
    The flags defined in settings are **always** used when compiling a new translation unit. They are **appended** to the ones generated from the external sources. Note, that the settings follow a hierarchy described in detail [here](../settings/#settings-hierarchy).

## Flags defined in settings
If you want to set the flag sources manually you can do it using the settings.
However, I strongly suggest to **NOT** do this and use a proper build system
instead. It will save you enormous amounts of time configuring the needed
include flags. However, if you know what you're doing, the main sources of
flags in settings:

- Flags defined in the `common_flags` [setting](../settings/#common_flags) -
  flags added to **each** compilation of every file. See the link for an
  example.
- Flags defined in the `lang_flags` [setting](../settings/#lang_flags) - flags
  added to each compilation in addition to the `common_flags` but only for a
  specific language.

## Flags defined in external flags sources

### Using CMake <small> (recommended) </small>

EasyClangComplete can search for `CMakeLists.txt` and generate a
`compile_commands.json` file from it. See next
[section](#using-a-compilation-database-compile_commandsjson) for details on
how this file is parsed.

To use `CMake` way of generating flags, make sure you set the `"flags_sources"`
in your settings. See how to set this setting correctly
[here](../settings/#flags_sources).

### Using a compilation database <small>`compile_commands.json`</small>
This file defines the flags per target (read more about it
[here](https://clang.llvm.org/docs/JSONCompilationDatabase.html)). When this
file is found, EasyClangComplete reads it and finds appropriate target given
the file which is currently opened by the user.

??? example "Example `compile_commands.json` file <small>(click to expand)</small>"
    ```json tab="compile_commands.json"
    [
        {
          "directory": "/main_dir",
          "command": "c++    -I/lib_include_dir    -o CMakeFiles/main_obj.o -c /home/user/dummy_main.cpp",
          "file": "/home/user/dummy_main.cpp"
        },
        {
          "directory": "/lib_dir",
          "command": "c++   -Dlib_EXPORTS  -fPIC   -o CMakeFiles/lib_obj.o -c /home/user/dummy_lib.cpp",
          "file": "/home/user/dummy_lib.cpp"
        }
    ]
    ```

!!! hint 
    The `compile_commands.json` does not contain header files. To complete
    header files we need to map them to an appropriate source file. By default,
    the plugin will try to search for the source file with matching name in the
    same folder as the header file. If this is not enough, use the setting
    `header_to_source_mapping`
    ([details](../settings/#header_to_source_mapping))
    in order to define a better mapping from header files to source ones.

### Using `.clang_complete` file
This is a simple text file where each line defines a single flag. Don't forget, that you must specify the flags fully here. The paths that are not absolute will be expanded from the location of the `.clang_complete` file. The same wildcards as in [settings](../settings/#common-path-wildcards) can be used here too.

??? example "Example `.clang_complete` file <small>(click to expand)</small>"
    ``` tab=".clang_complete"
    -I~.config/sublime-text-3/Packages/EasyClangComplete/src
    -I~.config/sublime-text-3/Packages/EasyClangComplete
    -Ilocal_folder
    -Wabi
    -std=c++14
    ```

    The first two lines will have `~` expanded to your home directory,
    `local_folder` will be appended to the location of the `.clang_complete`
    file, other flags will be keps intact.

## Flags generated from the compiler

Some flags can be generated from the compiler. These are governed by two
settings: [use_default_includes](../settings/#use_default_includes) and
[target_compilers](../settings/#target_compilers). These will run some command
over a chosen compiler, parse the result for the flags specific to the compiler
and will append these flags to the other ones. Click on the setting names above
to read more about them.

## Configurations that require manual actions
Some configurations cannot be configured without the knowledge that only the end user has. These usually include cases when the code generates files that must be included for proper code completions or when additional paths need to be provided to CMake when it is used as part of some other tool.

Below we will provide a list of the ones most commonly used.

??? note "Catkin setup <small>(click to expand)</small>"
    
    ### Catkin configuration

    For those using Catkin (e.g. when developing with
    [ROS](http://www.ros.org)) the plugin will configure the needed settings
    automatically if you are using Sublime Text projects. Here is a summary of
    what the plugin does for you. By default when running Sublime Text from GUI
    it knows nothing about the paths set in `.bashrc` of your system and
    therefore it cannot source your `devel` workspaces for you. Essentially
    sourcing the workspaces extends paths that Catkin uses to pass to CMake. So
    the plugin needs to update the `CMAKE_PREFIX_PATH` manually to be able to
    find `catkin`. Your `*.sublime-project` will look something like this after
    the configuration:

    ```json tab="*.sublime-project"
    "ecc_flags_sources": [
        {
          "file": "CMakeLists.txt",
          "prefix_paths": [ "/opt/ros/indigo",
                            "~/catkin_ws/devel" ]
        },
    ]
    ```

    !!! warning

        This will only work if you are using Sublime Text projects with your
        code. Otherwise no configuration will take place and the proper
        compiler flags will **NOT** be generated. You can set these settings
        also in yout **User** settings dropping the `ecc_` prefix, but this is
        not a recommended.

??? note "Qt setup <small>(click to expand)</small>"
    
    ### Qt configuration

    If you use Sublime Text for your Qt development and you use MOC files, you
    will need some additional setup. MOC generates header and source files from
    your `*.ui` files. These files are generated in the build folder of your
    project. As ECC uses a custom temporary location for your projects' CMake
    configuration it does not know about the real build location for your code
    (we might change this in the future, but this is the state for now). You
    will need to provide the build folder location in your flags.

    The best way to do this is to modify the `ecc_common_flags` setting in your
    Sublime Text project file (`*.sublime-project`). You will need to add a new
    include flag with the path to your build folder.

    !!! example

        For the sake of example let's consider that your project `my_project`
        gets built in a folder `~/YourBuildFolder/my_project`. Also, your code
        lies in `src` folder within the project. Then you will want to add the
        following include to your settings:

        ```json
        {
            "settings":
            {
                "ecc_common_flags":
                [
                    // Don't forget your other includes!
                    "-I~/YourBuildFolder/$project_name/src"
                ],
            }
        }
        ```

        This way ECC will add this path as an include path when compiling your
        code and will be able to find the header files generated by the MOC
        system.

    !!! tip "Tip: use wildcards!"

        Configuration is much easier if you use the available wildcards such as
        the `$project_name` seen in the example above. For a full list of
        available wildcards, see the
        [wildcards](../settings/#common-path-wildcards) section on the settings
        page.

    !!! tip "Tip: clean project after changing this setting"

        If changing the setting does not work, make use of the Clear CMake
        cache [command](../commands/#clear-cmake-cache) as ECC might still be
        using a cached version of the flags.

    !!! warning

        In my experience, the setting
        `ecc_use_target_compiler_built_in_flags` sometimes interferes with
        properly building Qt projects. So I recommend setting it to false:
        
        ```json
        "ecc_use_target_compiler_built_in_flags": false,
        ```
