# EasyClangComplete <small> auto-completion for human beings </small>

![Example](img/AutoComplete.gif)

[![Release][img-release]][release]
[![Downloads Month][img-downloads]][downloads]
[![GitHub build][img-github-actions]][github-actions]
[![Coverage Badge][img-coverage]][coverage]
[![Donate][img-paypal]][donate-paypal]


## **Simple start in just 3 steps!**

### **1. Install this plugin from [Package Control](https://packagecontrol.io/)** 

- In Sublime Text press <kbd>CTRL</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> and
  install `EasyClangComplete`

### **2. Install clang**
- **Ubuntu**        : `sudo apt-get install clang`
- **OSX**           : ships `clang` by default. You are all set!
- **Windows**       : install the latest release from clang website.
- **Other Systems** : use your package manager or install from clang website.
- clang website: http://llvm.org/releases/download.html

!!! tip
    Make sure `clang` is available in your `PATH` or that the setting [clang binary](settings/#clang_binary) is set to the full path to your `clang` binary.

    ??? info "Windows MSYS clang config <small>(click to expand)</small>" 

        On Windows, you can also use the `clang` binaries provided by
        [MSYS2](https://www.msys2.org/) with some additional configuration of
        the Sublime Text environment. The most convenient way to do this is to
        install the [Environment
        Settings](https://packagecontrol.io/packages/Environment%20Settings)
        package and configure it with settings similar to the following:

        ```json
        {
          "env": {
            "Windows": {
              "PATH": "C:\\msys64\\mingw64\\bin;C:\\msys64\\usr\\bin;%PATH%",
              "MSYSTEM": "MINGW64",
              "CHERE_INVOKING": "enabled_from_arguments"
            }
          }
        }
        ```

        This assumes MSYS2 is installed in the default location `C:\\msys64`,
        otherwise adjust the `PATH` variable accordingly. After a restart of
        Sublime Text, this will both make `clang` available by manipulating
        `PATH` and add some additional variables to set the MSYS2 environment.

        By changing `PATH` and `MSYSTEM`, it is also possible to switch between
        the different MSYS2 environments.

### **3. Configure your compiler flags and include folders**

#### CMake and .sublime-project
- Your code is inside a valid
  [`.sublime-project`](https://www.sublimetext.com/docs/3/projects.html)?
- You are using `CMake` as your build system?

You're in luck! The plugin will run cmake on a proper `CMakeLists.txt` in your
project folder and will use information from it to complete your code out of
the box! For more details, read [here](configs/#using-cmake-recommended).

!!! tip
    Make sure `cmake` is available in your `PATH` or that the setting [cmake binary](settings/#cmake_binary) is set to the full path to your `clang` binary.

#### Bazel <small>(Linux and MacOS only)</small>
If you have a Bazel project, just run the command `ECC: (Bazel) Generate compile_commands.json` to generate a compilation database file. The plugin can then use this database to complete your code.

#### Other options
If you cannot use CMake or Bazel in your project there are multiple ways to
configure the correct compiler flags. The plugin can use:

- Settings of the plugin: `common_flags` and `lang_flags`
- Compilation database: `compile_commands.json`.
- A `.clang_complete` file in the folder of the project.
- <small>(experimental)</small> `CppProperties.json` or `c_cpp_properties.json`
  files just like Visual Studio Code does.
- <small>(experimental)</small> `Makefile`: we can parse the recipes from a Makefile to generate proper flags.

You can read more in the [Configure compiler flags](configs.md) menu on
the left of this page.

## Things to do after setting up

### Dive into settings
There are numerous settings available for this plugin. You can find a
comprehensive review of all those settings and how to properly use them in the
[Full settings guide](settings.md) menu on the left of this page.

### Explore available commands
There is a number of commands that can be invoked from the command panel. See the full list in the [Available commands](commands.md) section.

## It's not you, it's me!
If this documentation cannot answer your question, or you have suggestions on
how to improve it, do not hesitate to fire up an
[issue](https://github.com/niosus/EasyClangComplete/issues).

## [**Support this project!**](support.md)

<script src="https://opencollective.com/easyclangcomplete/banner.js"></script>


[release]: https://github.com/niosus/EasyClangComplete/releases
[downloads]: https://packagecontrol.io/packages/EasyClangComplete
[github-actions]: https://github.com/niosus/EasyClangComplete/actions
[coverage]: https://app.codecov.io/gh/niosus/EasyClangComplete/branch/master
[gitter]: https://gitter.im/niosus/EasyClangComplete?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
[donate-paypal]: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=2QLY7J4Q944HS
[donate-flattr]: https://flattr.com/submit/auto?user_id=niosus&url=https://github.com/niosus/EasyClangComplete&title=EasyClangComplete&language=Python&tags=github&category=software
[libclang-issue]: https://github.com/niosus/EasyClangComplete/issues/88
[cmake-issue]: https://github.com/niosus/EasyClangComplete/issues/19
[bountysource-link]: https://www.bountysource.com/teams/easyclangcomplete
[beerpay]: https://beerpay.io/niosus/EasyClangComplete
[gratipay]: https://gratipay.com/EasyClangComplete/
[maintainerd]: https://github.com/divmain/maintainerd

[img-gratipay]: https://img.shields.io/gratipay/user/niosus.svg?style=flat-square
[img-beerpay]: https://beerpay.io/niosus/EasyClangComplete/badge.svg?style=flat-square
[img-bountysource]: https://img.shields.io/bountysource/team/easyclangcomplete/activity.svg?style=flat-square
[img-github-actions]: https://img.shields.io/github/checks-status/niosus/EasyClangComplete/master?style=flat-square
[img-coverage]: https://img.shields.io/codecov/c/gh/niosus/EasyClangComplete?style=flat-square&token=KJ8IuinGs1
[img-release]: https://img.shields.io/github/release/niosus/EasyClangComplete.svg?style=flat-square
[img-downloads]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=3600&style=flat-square
[img-downloads-month]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=2592000&style=flat-square
[img-subl]: https://img.shields.io/badge/Sublime%20Text-3-green.svg?style=flat-square
[img-mit]: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
[img-paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg?style=flat-square
[img-flattr]: https://img.shields.io/badge/Donate-Flattr-blue.svg?style=flat-square
[img-gitter]: https://badges.gitter.im/niosus/EasyClangComplete.svg?style=flat-square
[img-open-backers]: https://opencollective.com/easyclangcomplete/backers/badge.svg?style=flat-square
[img-open-sponsors]: https://opencollective.com/easyclangcomplete/sponsors/badge.svg?style=flat-square
