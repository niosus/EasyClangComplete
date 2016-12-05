Sublime Text 3 plugin that offers clang-based auto-completion for C++

# Let't get started! #
You're just two simple steps away from having code completions!

## 1. Install clang ##
- **Ubuntu**: `sudo apt-get install clang`
- **Windows**: install the latest release from `clang`
  [website](http://llvm.org/releases/download.html) (v >= 3.9)
- **OSX**: ships `clang` by default. You are all set!
- **Other Systems**: use your bundled package manager or install from `clang`
  [website](http://llvm.org/releases/download.html)

## 2. Configure your includes ##

### Using CMake? ###
Plugin will run cmake on a proper `CMakeLists.txt` in your project folder and
will use information from it to complete your code out of the box.

### Have a compilation database? ###
Plugin will search for a compilation database `compile_commands.json` in the
project folder and will load it to complete your code. If you want to specify a custom path to a comilation database you can do it in settings:
```json
"flags_sources": [
    {"file": "compile_commands.json", "search_in": "<YOUR_PATH>"},
  ],
```

### None of the above? ###
You will need a little bit of manual setup for now. `Clang` will automatically
search for headers in the folder that contains the file you are working on and
its parent. If you have a more sophisticated project you will need to help
`clang` just a little bit. There are three ways to do it.

Pick *ANY* of the following:

- Set include dirs in `"common_flags"` setting in `User Settings`:
  + See default [settings](EasyClangComplete.sublime-settings) to get started.
    These flags will be included in every project you run.
- Add `.clang_complete` file to the root of your project folder.
  + This file should contain all includes and macroses you want to use.
  + Example:
  ```
  -Isrc
  -I/usr/include
  ```
- Override `"common_flags"` setting in your project file! Just define the same
  setting in project specific settings with either one of two prefixes:
  `"ecc_"` or `"easy_clang_complete_"`. See the project file in this repo for a
  working example. Minimal example for clarity:

  ```json
  {
    "settings":
    {
      "ecc_common_flags": ["-Isrc", "-I/usr/include"],
      "easy_clang_complete_verbose": true
    }
  }
  ```

## That's it! You're ready to use the plugin! ##

## More info here ##
Get more info in a readme:
https://github.com/niosus/EasyClangComplete/blob/master/README.md

Please see the default settings [file](EasyClangComplete.sublime-settings)
shipped with the plugin for explanations and sane default values.

## Thanks ##
It is really important for me that you are using the plugin. If you have
problems - submit issues and we will eventually solve them together.

If you like the plugin, consider supporting the development! It takes me quite
some time to implement everything as good as I can. Find ways to support the
plugin here: https://github.com/niosus/EasyClangComplete#support-it
