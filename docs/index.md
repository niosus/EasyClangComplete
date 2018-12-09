# EasyClangComplete <small> auto-completion for human beings </small>

![Example](img/AutoComplete.gif)

[![Release][img-release]][release]
[![Downloads Month][img-downloads]][downloads]
[![Travis Build][img-travis]][travis]
[![Windows Build][img-appveyor]][appveyor]
[![Codacy Badge][img-codacy]][codacy]
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

### **3. Configure your compiler flags and include folders**

#### CMake and .sublime-project
- Your code is inside a valid
  [`.sublime-project`](https://www.sublimetext.com/docs/3/projects.html).
- You are using `CMake` as your build system.

You're in luck! The plugin will run cmake on a proper `CMakeLists.txt` in your
project folder and will use information from it to complete your code out of
the box! For more details, read [here](configs/#using-cmake-recommended).

!!! tip
    Make sure `cmake` is available in your `PATH` or that the setting [cmake binary](settings/#cmake_binary) is set to the full path to your `clang` binary.

#### Other options
If you cannot use `CMake` in your project there are multiple ways to configure
the correct compiler flags. The plugin can use:

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



[release]: https://github.com/niosus/EasyClangComplete/releases
[downloads]: https://packagecontrol.io/packages/EasyClangComplete
[travis]: https://travis-ci.org/niosus/EasyClangComplete
[appveyor]: https://ci.appveyor.com/project/niosus/easyclangcomplete/branch/master
[codacy]: https://www.codacy.com/app/zabugr/EasyClangComplete/dashboard
[coverage]: https://www.codacy.com/app/zabugr/EasyClangComplete/dashboard
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
[img-appveyor]: https://img.shields.io/appveyor/ci/niosus/easyclangcomplete/master.svg?style=flat-square&label=windows
[img-travis]: https://img.shields.io/travis/niosus/EasyClangComplete/master.svg?style=flat-square&label=linux%20|%20osx
[img-codacy]: https://img.shields.io/codacy/grade/254f8db44b004dffa76b8cebfece4c06.svg?style=flat-square&label=quality
[img-coverage]: https://img.shields.io/codacy/coverage/254f8db44b004dffa76b8cebfece4c06.svg?style=flat-square
[img-release]: https://img.shields.io/github/release/niosus/EasyClangComplete.svg?style=flat-square
[img-downloads]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=3600&style=flat-square
[img-downloads-month]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=2592000&style=flat-square
[img-subl]: https://img.shields.io/badge/Sublime%20Text-3-green.svg?style=flat-square
[img-mit]: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
[img-paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg?style=flat-square
[img-flattr]: https://img.shields.io/badge/Donate-Flattr-blue.svg?style=flat-square
[img-gitter]: https://badges.gitter.im/niosus/EasyClangComplete.svg?style=flat-square
