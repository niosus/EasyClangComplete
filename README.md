# EasyClangComplete #

Plugin for Sublime Text 3 for easy to use, out of the box autocompletions for C
and C++.

![Example](pics/autocomplete_show_off.gif)

[![Release][img-release]][release]
[![Travis Build][img-travis-linux]][travis]
[![Travis Build][img-travis-osx]][travis]
[![Windows Build][img-appveyor]][appveyor]
[![Codacy Badge][img-codacy]][codacy]
[![Coverage Badge][img-coverage]][coverage]
[![Downloads Month][img-downloads-month]][downloads]
[![MIT licensed][img-mit]](./LICENSE)

[![Bountysource][img-bountysource]][bountysource-link]
[![Flattr this git repo][img-flattr]][donate-flattr]
[![Donate][img-paypal]][donate-paypal]

# Jump right in! #
Follow all the following steps to ensure the plugin works as expected!

## Install this plugin ##
- Best is to use [Package Control](https://packagecontrol.io/installation)
  + <kbd>CTRL</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> and install
    `EasyClangComplete`
- If you don't have Package Control (you should)
  + download one of the releases from
    [here](https://github.com/niosus/EasyClangComplete/releases).

## Install clang ##
- **Ubuntu**: `sudo apt-get install clang`
- **Windows**: install the latest release from `clang`
  [website](http://llvm.org/releases/download.html) (v >= 3.9)
- **OSX**: ships `clang` by default. You are all set!
- on other systems refer to their package managers or install from `clang`
  [website](http://llvm.org/releases/download.html)

## Configure your includes ##

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
  -I/opt/ros/indigo/include
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

# More on the plugin #
All the essential information to make the plugin run is written above. If you
are still interested in more details - please read on.

## General info ##
The plugin has two modes:

- [DEFAULT]: uses `libclang` with its python bindings. This is the better
  method as it fully utilizes saving compilation database which makes your
  completions blazingly fast. It is a default method. It is also unit tested to
  complete STL functions on Linux and OSX platforms. It will also fully work
  for Windows as soon as clang 4.0 is released. See [issue][libclang-issue]
- [FALLBACK]: one that parses the output from
  `clang -Xclang -code-completion-at` run from the command line. This is a fallback method if something is wrong with the first one.

This plugin is intended to be easy to use. It should autocomplete STL out of
the box and is capable of working with multiple flag storages, such as a
compilation database or a `.clang_complete` file. If you experience problems -
create an issue. I will try to respond as soon as possible.

## Commands ##
Here are some highlights for the commands. You can see all commands in command
pallet. Open it by pressing:

- Windows/Linux: <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>
- OSX: <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>

All the commands of this plugin start with `EasyClangComplete:` and should be
self explanatory. Open an issue if they are not.


## Settings ##

Please see the default settings [file](EasyClangComplete.sublime-settings)
shipped with the plugin for explanations and sane default values.

**PLEASE RESTART SUBLIME TEXT AFTER EACH SETTINGS CHANGE**

## Credits ##
The whole work seen here was originally a fork of another repository:
[ClangAutoComplete](https://github.com/pl-ca/ClangAutoComplete)

However, with time this plugin has grown quite different from its origin and
this is why you see it as a separate package now. Anyway, I encourage you to
check out what `ClangAutoComplete` has to offer and come back if you still like
this plugin more.

The trick with multiple `clang.cindex` files is inspired by this repo:
[clangHelper](https://github.com/griebd/clangHelper). Thanks for inspiration!

If you are an experienced python developer and find that something in my code
sucks completely - **DO** tell me. Python is not my main language and I am
always willing to learn.

Some functionality is there only because of the help of the following users (in no particualr order):

@Ventero, @riazanovskiy, @rchl, @Mischa-Alff, @jdumas, @simia, @tastytea,
@brupelo, @randy3k.

## Tests ##
Most crucial functionality is covered with unit tests using
[UnitTesting](https://github.com/randy3k/UnitTesting) Sublime Text plugin.

## Contributing ##
Contributions are welcome! Look at the issue list. If there is something you
think you can tackle, write about it in that issue and submit a PR.

Code style:
- Line width is `80` characters
- Every public function should be documented.
- The code passes linters:
  + `pep8`
  + `pep257`: ignoring `["D209", "D203", "D204"]`

Please ensure, that your code conforms to this.

# Support it! #
[![Bountysource][img-bountysource]][bountysource-link]
[![Flattr this git repo][img-flattr]][donate-flattr]
[![Donate][img-paypal]][donate-paypal]

Current sponsor of this project is my sleep.
Please buy me a cup of tea if you appreciate the effort.

Also, pull requests are welcome! And don't forget to tell people about this
plugin! The more people use it - the merrier.

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

[img-bountysource]: https://img.shields.io/bountysource/team/easyclangcomplete/activity.svg
[img-appveyor]: https://img.shields.io/appveyor/ci/niosus/easyclangcomplete/master.svg?label=windows
[img-travis-linux]: https://img.shields.io/travis/niosus/EasyClangComplete/master.svg?label=linux
[img-travis-osx]: https://img.shields.io/travis/niosus/EasyClangComplete/master.svg?label=osx
[img-codacy]: https://img.shields.io/codacy/grade/254f8db44b004dffa76b8cebfece4c06.svg
[img-coverage]: https://img.shields.io/codacy/coverage/254f8db44b004dffa76b8cebfece4c06.svg
[img-release]: https://img.shields.io/github/release/niosus/EasyClangComplete.svg?maxAge=3600
[img-downloads]: https://img.shields.io/packagecontrol/dt/EasyClangComplete.svg?maxAge=3600
[img-downloads-month]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=2592000
[img-subl]: https://img.shields.io/badge/Sublime%20Text-3-green.svg
[img-mit]: https://img.shields.io/badge/license-MIT-blue.svg
[img-paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg
[img-flattr]: https://img.shields.io/badge/Donate-Flattr-blue.svg
[img-gitter]: https://badges.gitter.im/niosus/EasyClangComplete.svg
