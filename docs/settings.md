**This is a comprehensive guide on how to set the settings correctly and what they are used for.**

# flags_sources
This setting defines where to search for flags for each compilation target. You
can read more about different ways of configuration and pick the one that suits
you most in the [Configuration](configs.md) section.

## How is the setting parsed ##
This setting consists of a list of json structs and it is prioritized from top
to bottom. The higher the source is in the list the earlier it will be checked.
In the example [below](#below) the plugin will try to find `CMakeLists.txt`
file first and will stop if it succeeds. If it cannot find it the search
continues for `compile_commands.json` and so on till the end of the list.

## Additional settings ##
You can set an additional option for all of the settings:

- `"search_in":` defines a *folder* where the file will be searched for

CMake entry has some more specific settings:

- `"flags":` defines a list of flags that will be passed to cmake with `-D`
  prefix, see example below
- `"prefix_paths":` a list of folders to be appended to `CMAKE_PREFIX_PATH`
  when running the `cmake` command

Any of the sub-settings can be omitted.

## Example ##
```json
  "flags_sources": [
    {
        "file": "CMakeLists.txt",
        "flags": ["BLAH"],
        "prefix_paths": ["<SOME_PREFIX_PATH>"],
    },
    {
        "file": "compile_commands.json",
        "search_in": "<SOME_FOLDER>"
    },
    {"file": ".clang_complete"},
  ]
```

This is what will happen in order:

1. The plugin will search for `CMakeLists.txt` up the tree from the current
   file. When the appropriate file is found, the following two commands take
   place:
       - `<SOME_PREFIX_PATH>` is appended to `CMAKE_PREFIX_PATH` in a local
         copy of the environment
       - `cmake` is run as follows: `cmake -DBLAH <FOUND_CMAKELISTS_FILE>` from
         within a temporary folder generated for this project
2. The plugin will search for `compile_commands.json` in `<SOME_FOLDER>`. If it
   finds it there it loads the flags from it, if not it continues to the next
   flag source. It does *NOT* continue searching for `compile_commands.json` up
   the tree as the user has specifically provided a folder to search in.
3. The plugin searches for `.clang_complete` file up the tree and loads the
   flags from it if it is found. Otherwise the only flags being used are the
   ones defined in the `"common_flags"`.
