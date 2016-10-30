# EasyClangComplete #

Sublime Text 3 plugin that offers clang-based auto-completion for C++

![Example](autocomplete_show_off.gif)

|           Linux / OSX           |               Windows               |
|:-------------------------------:|:-----------------------------------:|
| [![Status][img-travis]][travis] | [![Status][img-appveyor]][appveyor] |

[![Release][img-release]][release]
[![Downloads][img-downloads]][downloads]
[![Downloads Month][img-downloads-month]][downloads]
[![Codacy Badge][img-codacy]][codacy]
[![MIT licensed][img-mit]](./LICENSE)
[![Gitter][img-gitter]][gitter]
[![Flattr this git repo][img-flattr]][donate-flattr]
[![Donate][img-paypal]][donate-paypal]

Plugin for easy-to-use, minimal-setup autocompletions for C++ for Sublime Text
3. [Support](#support-it) it if you like it.

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

### Are you using CMake? ###
Plugin automatically generates `.clang_complete` and uses it for building our
code.

### Not using CMake? ###
You will need a little bit of manual setup for now. `Clang` will automatically
search for headers in the folder that contains the file you are working on and
its parent. If you have a more sophisticated project you will need to help
`clang` just a little bit. There are three ways to do it. Pick any of the
following:

- Set `include_dirs` setting in `User Settings`:
  + see default [settings](EasyClangComplete.sublime-settings) to get started.
    These includes will be included in every project you run.
- Add `.clang_complete` file to the root of your project folder.
  + this file should contain all includes and macroses you want to use.
  + see example [.clang_complete](.clang_complete) file.
  + absolute paths start with `/`. All the others are treated as relative.
- Add all the flags to pass to clang to `*.sublime-project` file.
  + add all settings as a string list under `settings` -> `clang_flags`.
  + See example [sublime-project](easy_clang_complete.sublime-project#L22)
    file.
  + absolute paths start with `/`. All the others are treated as relative.

## That's it! You're ready to use the plugin! ##

# More on the plugin #
All the essential information to make the plugin run is written above. If you
are still interested in more details - please read on.

## General info ##
The plugin has two modes:

- one that uses `libclang` with its python bindings. This is the better method
  as it fully utilizes saving compilation database which makes your completions
  blazingly fast. It is a default method. It is also unit tested to complete
  STL functions on Linux and OSX platforms. It will also work for Windows as
  soon as clang 4.0 is released. See [issue][libclang-issue]
- one that parses the output from `clang -Xclang -code-completion-at` run from
  the command line. This is a fallback method if something is wrong with the
  first one.

This plugin is intended to be easy to use. It should autocomplete STL out of
the box and you should just add the folders your project uses as includes to
the flags in the settings to make it autocomplete code all your project. If you
experience problems - create an issue. I will try to respond as soon as
possible.

## Commands ##
Here are some highlights for the commands. You can see all commands in command
pallet. Open it by pressing:

- Windows/Linux: <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>
- OSX: <kbd>Cmd</kbd> + <kbd>Shift</kbd> + <kbd>P</kbd>

All the commands of this plugin start with `EasyClangComplete:` and should be
self explanatory. Open an issue if they are not.


## Settings highlights ##

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

@Ventero, @riazanovskiy, @rchl, @Mischa-Alff, @jdumas.

## Tests ##
I have tried to cover most crucial functionality with unit tests using
[UnitTesting](https://github.com/randy3k/UnitTesting) Sublime Text plugin.
Currently tests cover autocompletion of user struct and stl vector. To check
out the current status click on relevant badge below:

|           Linux / OSX           |               Windows               |
|:-------------------------------:|:-----------------------------------:|
| [![Status][img-travis]][travis] | [![Status][img-appveyor]][appveyor] |

# Support it! #
[![Flattr this git repo][img-flattr]][donate-flattr]
[![Donate][img-paypal]][donate-paypal]

Current sponsor of this project is my sleep.
Please buy me a cup of tea if you appreciate the effort.

[release]: https://github.com/niosus/EasyClangComplete/releases
[downloads]: https://packagecontrol.io/packages/EasyClangComplete
[travis]: https://travis-ci.org/niosus/EasyClangComplete
[appveyor]: https://ci.appveyor.com/project/niosus/easyclangcomplete/branch/master
[codacy]: https://goo.gl/h52rHl
[gitter]: https://gitter.im/niosus/EasyClangComplete?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge
[donate-paypal]: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=2QLY7J4Q944HS
[donate-flattr]: https://flattr.com/submit/auto?user_id=niosus&url=https://github.com/niosus/EasyClangComplete&title=EasyClangComplete&language=Python&tags=github&category=software
[libclang-issue]: https://github.com/niosus/EasyClangComplete/issues/88
[cmake-issue]: https://github.com/niosus/EasyClangComplete/issues/19


[img-appveyor]: https://ci.appveyor.com/api/projects/status/4h4lfyomah06om2t/branch/master?svg=true
[img-travis]: https://travis-ci.org/niosus/EasyClangComplete.svg?branch=master
[img-codacy]: https://goo.gl/PDVYTj
[img-release]: https://img.shields.io/github/release/niosus/EasyClangComplete.svg?maxAge=3600
[img-downloads]: https://img.shields.io/packagecontrol/dt/EasyClangComplete.svg?maxAge=3600
[img-downloads-month]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=2592000
[img-subl]: https://img.shields.io/badge/Sublime%20Text-3-green.svg
[img-mit]: https://img.shields.io/badge/license-MIT-blue.svg
[img-paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg
[img-flattr]: https://img.shields.io/badge/Donate-Flattr-blue.svg
[img-gitter]: https://badges.gitter.im/niosus/EasyClangComplete.svg
