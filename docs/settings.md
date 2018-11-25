# Three levels of settings for EasyClangComplete
- Default settings <small>(shipped with the plugin)</small>
- Global user settings <small>(defined globally for the whole plugin)</small>
- Project settings <small> (defined in a [`.sublime-project`][subl-proj] file for a specific project)
  </small>

!!! warning 
    Project-related settings will only work when your code has a
    `.sublime-project` file related to it. For documentation on using the
    Sublime Text projects please refer [here][subl-proj].

## Settings hierarchy
1. If no settings are defined the **Default** ones are used
2. **User** settings have precedence over the **Default** ones
3. **Project** settings have precedence over the **User** and **Default** ones

## Common path wildcards
Every path variable in settings can contain wildcards:

- `$project_base_path` is replaced by the full path to the project to which
  the currently opened view belongs.
- `$project_name` is replaced by the name of the current project.
- `$clang_version` is replaced by the numeric version of used clang.
- `~` is replaced by the path to user home directory.
- `*` when put at the end of folder path expands to all folders in that
  folder. Not recursive.

## Using environmental variables
In addition to the variables described above, you can use your environment
variables:

- OSX and Linux: `$variable_name` or `${variable_name}`
- Windows: `$variable_name`, `${variable_name}` or `%variable_name%`

## How to define project settings
The project-specific settings are only available when the code is within a Sublime Text project defined by a `*.sublime-project` file. They must be stored under the `"settings"` tab in the project file with either of the two prefixes: `ecc_` or `easy_clang_complete_`. See example below for more clarifications.

!!! example "Example of setting `verbose` and `use_libclang` project-specific settings"
    ```json tab="my_project.sublime-project"
    {
        "settings": {
            "easy_clang_complete_verbose": true,
            "ecc_use_libclang": true,
        }
    }
    ```
    
    Note that for `verbose` setting a prefix `easy_clang_complete_` is used,
    while for `use_libclang` we use `ecc_` prefix.

!!! note "Project settings override User and Default settings"
    The settings defined in the `*.sublime-project` file override User and Default settings. Keep that in mind when specifying them! They are **not appended**, they **override** these settings.

## Complete settings list
This is a complete guide over all settings. Here we look at every setting in
detail, explain where they are used and what are their default values.

### **`common_flags`**
Specify common flags that are passed to clang for **every** compilation. These
usually include common include paths that are needed for finding STL etc. Below
are typical defaults for Linux.

??? example "Good defaults for Linux & MacOS <small>(click to expand)</small>"
    ```json  
    "common_flags" : [
      "-I/usr/include",
      "-I$project_base_path/src",
      // this is needed to include the correct headers for clang
      "-I/usr/lib/clang/$clang_version/include",
    ],
    ```

??? example "Good defaults for Windows with MinGW <small>(click to expand)</small>"
    ```json  
    "common_flags" : [
        "-IC:\\MinGW\\lib\\gcc\\mingw32\\6.3.0\\include\\c++",
        "-IC:\\MinGW\\lib\\gcc\\mingw32\\6.3.0\\include\\c++\\mingw32"
    ],
    ```

    Here I have installed MinGW from [MinGW downloads page](https://osdn.net/projects/mingw/releases/). Everything seems to work including the STL support.

### **`lang_flags`**
These flags are language-specific. They prepend `common_flags` when compiling files of a particular language. This is a good place to define flags for a standard library etc.

!!! example "Default value"
    ```json
    "lang_flags": {
      "C": ["-std=c11"],
      "CPP": ["-std=c++11"],
      "OBJECTIVE_C": ["-std=c11"],
      "OBJECTIVE_CPP": ["-std=c++11"],
    },
    ```

!!! warning 
    When specifying this setting in your user or project settings make sure to
    keep ALL language keys.

### **`flags_sources`**
This setting defines external sources for the compilation flags. If you have a
build system <small>(e.g. CMake)</small> in place or have an external file that
defines all the compilation flags for your project <small>(e.g. a compilation
database `compile_commands.json`)</small>, you can load the flags directly from
there. For more details on differences between the flag sources refer to [this
page](../configs/#geting-correct-compiler-flags) of the documentation.

!!! tip "`common_flags` and `lang_flags` are never overridden by external flag sources"
    The flags from [`common_flags`](#common_flags-flags-added-to-each-compilation) and from [`lang_flags`](#lang_flags-language-specific-flags) are **ALWAYS** present in the compilation. The flags loaded from the flag sources are appended to those and **DO NOT OVERRIDE** them.

#### Possible options
- `"file"` <small>MANDATORY</small> - defines the name of the flags source. Can
  be one of:
    + `"CMakeLists.txt"` <small> looks for a `CMakeLists.txt` file that
      contains a line that starts with `"project"` in it </small>
    + `"compile_commands.json"`
    + `"CppProperties.json"`
    + `"c_cpp_properties.json"`
    + `".clang_complete"`
    + `"Makefile"`
- `"search_in": <path>` <small>OPTIONAL</small> - defines a *folder* in which
  the file should be searched. If it is not defined, the search starts from the current file up the directory tree. 

#### CMake-specific options
CMake is handled in a special way and there are additional settings that can be specified for this type of flag source:

- `"flags": [<flags>]` <small>OPTIONAL</small> - defines a list of flags that can be passed to the `cmake` program upon calling it
- `"prefix_paths": [<paths>]` <small>OPTIONAL</small> - defines a list of paths that will be set as prefix paths when running `cmake`

#### Search order
The flag sources are searched in a strictly hierarchical order from top to
bottom. First the top-most `"file"` is searched for. If this search fails, the
second `"file"` is searched. This continues until either one of the flag
sources is found or the list has finished. See example below for more
explanations.

??? example "Example flag sources <small>(click to expand)</small>"
    In this example we define a number of flag sources with some additional options:
    ```json
    "flags_sources": [
      {
        "file": "CMakeLists.txt",
        "flags":
        [
          "-DCMAKE_BUILD_TYPE=Release",
        ],
        "prefix_paths": ["/opt/ros/indigo"]
      },
      {
        "file": "Makefile"
      },
      {
        "file": ".clang_complete"
      }
    ],
    ```
    Here, first the plugin tries to find a `CMakeLists.txt` with `project(<smth>)` inside of it. If this is successful, then it invokes a command 
    ```bash
    cmake -DCMAKE_PREFIX_PATHS=/opt/ros/indigo -DCMAKE_BUILD_TYPE=Release <folder_to_CMakeLists.txt>
    ```
    storing the generated files in a temporary build folder.

    If the `CMakeLists.txt` file cannot be found, the plugin continues to search for a `Makefile` and if that fails - for a `.clang_complete` file

### **`show_errors`**

When this option is `true` the errors will be highlighted upon every file save.

!!! example "Default value"
    ```json
    "show_errors": true,
    ```

### **`gutter_style`**

Defines the style of the gutter icon shown on the sidebar.

#### Possible values
- ![image](img/error_color.png): `"color"` <small>default</small>
- ![image](img/error_mono.png): `"mono"` 
- ![image](img/error_dot.png): `"dot"` 
- `"none"`

!!! example "Default value"
    ```json
    "gutter_style": "color",
    ```

### **`triggers`**

Defines all characters that trigger auto-completion. The default value is:

!!! example "Default value"
    ```json
    "triggers" : [ ".", "->", "::", " ", "  ", "(", "[" ],
    ```

### **`valid_lang_syntaxes`**

A dictionary that defines a mapping from language to an array of valid
syntaxes for it. The values here are good defaults, but feel free to
customize the list to your liking. When modifying this setting make sure
that all 4 languages have values.

!!! example "Default value"
    ```json
    "valid_lang_syntaxes": {
    "C":              ["C", "C Improved", "C99"],
    "CPP":            ["C++", "C++11"],
    "OBJECTIVE_C":    ["Objective-C"],
    "OBJECTIVE_CPP":  ["Objective-C++"]
    },
    ```

!!! warning 
    When specifying this setting in your user or project settings make sure to
    keep ALL language keys.

### **`ignore_list`**
Do not run the plugin for any files that match these paths. Use
`glob/fnmatch` shell-style filename expansion. In addition, you can still use
`'~'` to mark the home directory.

!!! example "Default value"
    ```json
    "ignore_list": [
        "~/some_folder/*",
        "/some/absolute/file.ext",
        "$project_base_path/some/project/path/*",
    ],
    ```

### **`use_libclang`**

If set to `true` will use `libclang` through python bindings. This offers much better performance generally, but can be buggy on some systems. When set to `false` will use clang_binary and parse the output of `clang -Xclang -code-complete-at <some_file>` instead.

!!! example "Default value"
    ```json
    "use_libclang" : true,
    ```

### **`use_default_includes`**

If set to `true` there will be default includes added to the `"common_flags"`. We generate these includes from running the following command on some empty temp file `test.cc`:

```bash
<clang_binary> -c test.cc -v 
```

See [`clang_binary`](#clang_binary) setting for more details on what clang binary will be in use.

!!! example "Default value"
    ```json
    "use_default_includes" : true,
    ```

### **`verbose`**

Output lots of additional information in the console. Useful for debugging. Off by default.

!!! example "Default value"
    ```json
    "verbose" : false,
    ```

### **`include_file_folder`**

Add the folder with current file with `-I` flag.

!!! example "Default value"
    ```json
    "include_file_folder" : true,
    ```

### **`include_file_parent_folder`**

Add the parent folder of the current file's one with `-I` flag

!!! example "Default value"
    ```json
    "include_file_parent_folder" : true,
    ```

### **`clang_binary`**


Pick the clang binary used by the plugin. This is used to determine the
version of the plugin and pick correct libclang bindings or for code completion when the setting [`use_libclang`](#use_libclang) is set to `false`.

!!! example "Default value"
    ```json
    "clang_binary" : "clang++",
    ```

### **`cmake_binary`**

Pick the binary used for `cmake`. 

!!! example "Default value"
    ```json
    "cmake_binary" : "cmake",
    ```

!!! warning
    Please make sure the binary you provide is accessible from the command line on your system.

### **`autocomplete_all`**

Ignore triggers and try to complete after each character

!!! example "Default value"
    ```json
    "autocomplete_all" : false,
    ```

!!! danger
    Can be very slow! Enable only if you know what you are doing!

### **`hide_default_completions`**

Hide the completions generated by Sublime Text and other plugins.

!!! example "Default value"
    ```json
    "hide_default_completions": false,
    ```

### **`max_cache_age`**

Plugin uses smart caching to not load the data for the translation units (TUs)
more times than needed. To save space we want to clear the unused data, so we
remove cache data older than specified time.

!!! tip
    - Minimum value is 30 seconds.
    - Format: `<hours>:<minutes>:<seconds>: "HH:MM:SS"`.

!!! example "Default value"
    ```json
    "max_cache_age": "00:30:00",
    ```

### **`show_type_info`**

Show additional information on hover over function call/variable etc.
This replaces default sublime on hover behavior.

!!! example "Default value"
    ```json
    "show_type_info": true,
    ```

### **`show_type_body`**

Show body of struct/class/typedef declaration in a tooltip invoked by calling
info enabled by the setting
[`show_type_info`](/#show_type_info).

!!! example "Default value"
    ```json
    "show_type_body" : true,
    ```

### **`libclang_path`**

On some esoteric systems we cannot find `libclang` properly.
If you know where your `libclang` is - set the full path here. This setting generally should not be needed.

!!! example "Default value"
    ```json
    "libclang_path": "<some_path_here>",
    ```

### **`progress_style`**

Pick the progress style. There are currently these styles available:

- `ColorSublime` : ⣾⣽⣻⢿⡿⣟⣯⣷
- `Moon`         : 🌑🌒🌓🌔🌕🌖🌗🌘
- `None`

!!! example "Default value"
    ```json
    "progress_style": "Moon",
    ```

### **`use_libclang_caching`**

Controls if `libclang` caches the results. This works faster, but in rare cases
can generate wrong completions. Usually it works just fine, so it is `true` by
default.

!!! example "Default value"
    ```json
    "use_libclang_caching": true,
    ```

### **`header_to_source_mapping`**

Templates to find source files for headers in case we use a compilation
database: Such a DB does not contain the required compile flags for header
files. In order to find a best matching source file instead, you can use
templates. Such templates describe how to find (relative to the header file) a
source file which we can use to get compile flags for. In the simplest case,
one can just use the (relative) path to where the source files are relative to
your header file. For example, if your headers are in a subdirectory `"inc"`
and your sources in a subdirectory `"src"` next to the first one, then you can
use `"../src/"` as lookup. If needed, you can also use finer granular lookup
templates by using UNIX style globbing patterns and placeholders. Placeholders
are of the form `'{placeholdername}'`. The following placeholders can be used:

- `basename:`  The base file name without the directory part.
- `stamp:`     Like `"basename"`, but with the file name extension removed.
- `ext:`       The file name extension of the header file.

??? example "Default header - source mappings <small>(click to expand)</small>"
    ```json
    "header_to_source_mapping": [
        // Look for related files in the header's directory:
        "./",

        // And in the "src" directory:
        "../src/",

        // And in the "source" directory:
        "../source/",

        // Example: Use flags but only from the source file
        // belonging to the header in question:
        // "{stamp}.cpp",

        // Example: Use flags from a file with an
        // "exotic" file name suffix:
        // "{stamp}.mycustomext
    ],
    ```

### **`use_target_compiler_built_in_flags`**

Controls if we try to retrieve built-in flags from the target compiler. This
option is used when we use a `compile_commands.json` file either directly or
indirectly e.g. via CMake. If set to true, we try to ask the compiler for the
defines and include paths it sets implicitly and pass them to the clang
compiler which is used to generate the code completion.If your completions
require the knowledge about the toolchain, this option should improve the
quality of the completions, however, in some corner cases it might cause
completions to fails entirely.

!!! example "Default value"
    ```json
    "use_target_compiler_built_in_flags": false,
    ```

### **`target_xxx_compiler`**
 <small>(xxx - is a language)</small>
The below options allow to set the actual target compilers (i.e. the one you
use in your build chain). If they are set, we will ask the compilers for their
built in flags (defines and include paths) and pass them to the clang compiler
to generate code completions. This is especially useful when working with
non-host tool chains, where the compilers might set additional target specific
defines which are now seen by the (host) clang compiler. Note: These settings
are only used if the target compiler cannot be retrieved otherwise, e.g. from a
`compile_commands.json` file. Note: The set compilers will also be passed to
CMake if you use it as source.

!!! example "Default value"
    ```json
    "target_c_compiler": null,
    "target_cpp_compiler": null,
    "target_objective_c_compiler": null,
    "target_objective_cpp_compiler": null,
    ```

### **`expand_template_types`**

Expand template types and add more hyperlinks when showing info on hover. For
example, `std::shared_ptr<Foo> foo` will expand to show hyperlinks to both
`std::shared_ptr` and the template type, `Foo`. This may cause some types and
typedefs to be verbose. For example, `std::string foo` expands to
`std::string<char, char_traits<char>, allocator<char>> foo`.
  
!!! example "Default value"
    ```json
    "expand_template_types": true,
    ```

[subl-proj]: https://www.sublimetext.com/docs/3/projects.html
