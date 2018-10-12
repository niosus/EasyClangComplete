# EasyClangComplete #

Plugin for Sublime Text 3 for easy to use, out of the box autocompletions for
C, C++, Objective-C, and Objective-C++.

![Example](pics/autocomplete.gif)

[![Release][img-release]][release]
[![Downloads Month][img-downloads]][downloads]
[![Travis Build][img-travis]][travis]
[![Windows Build][img-appveyor]][appveyor]
[![Codacy Badge][img-codacy]][codacy]
[![Coverage Badge][img-coverage]][coverage]
[![Donate][img-paypal]][donate-paypal]
[![Bountysource][img-bountysource]][bountysource-link]

# Simple start in just 3 steps! #

## 1. Install this plugin ##
- In Sublime Text press <kbd>CTRL</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> and
  install **EasyClangComplete** using [Package Control](https://packagecontrol.io/installation).

## 2. Install clang ##
- **Ubuntu**        : `sudo apt-get install clang`
- **OSX**           : ships `clang` by default. You are all set!
- **Windows**       : install the latest release from clang website.
- **Other Systems** : use your package manager or install from clang website.
- clang website: http://llvm.org/releases/download.html

## 3. Configure your compiler flags and include folders ##

#### Do you use CMake?
You're in luck! The plugin will run cmake on a proper `CMakeLists.txt` in your
project folder and will use information from it to complete your code out of
the box! For more details, read the plugin
[docs](https://niosus.github.io/EasyClangComplete/configs/#using-cmake-recommended)
about CMake.

#### Don't like CMake?
Don't worry! There are plenty of ways to configure the plugin! Read the
[related documentation](https://niosus.github.io/EasyClangComplete/configs/)
for more info!

## Extensive documentation
There are so many things I want to tell you! There is so much the plugin is
capable of! Read the [docs](https://niosus.github.io/EasyClangComplete/) to get
started!


## Contribute to the project
This project exists thanks to all the people who contribute. Feel free to open
an issue if something is not clear or a PR if you want to implement some
missing functionality or fix a bug. Check out the contribution
[guide](.github/CONTRIBUTING.md) for that.

## [Support this project!](https://niosus.github.io/EasyClangComplete/support/)

<a href="graphs/contributors"><img src="https://opencollective.com/EasyClangComplete/contributors.svg?width=890&button=false" /></a><a href="https://opencollective.com/EasyClangComplete#backers" target="_blank"><img src="https://opencollective.com/EasyClangComplete/backers.svg?width=890"></a>

<a href="https://opencollective.com/EasyClangComplete/sponsor/0/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/0/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/1/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/1/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/2/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/2/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/3/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/3/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/4/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/4/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/5/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/5/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/6/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/6/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/7/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/7/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/8/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/8/avatar.svg"></a>
<a href="https://opencollective.com/EasyClangComplete/sponsor/9/website" target="_blank"><img src="https://opencollective.com/EasyClangComplete/sponsor/9/avatar.svg"></a>



                         ╔═╗┌─┐┌─┐┬ ┬  ╔═╗┬  ┌─┐┌┐┌┌─┐  ╔═╗┌─┐┌┬┐┌─┐┬  ┌─┐┌┬┐┌─┐
                         ║╣ ├─┤└─┐└┬┘  ║  │  ├─┤││││ ┬  ║  │ ││││├─┘│  ├┤  │ ├┤
                         ╚═╝┴ ┴└─┘ ┴   ╚═╝┴─┘┴ ┴┘└┘└─┘  ╚═╝└─┘┴ ┴┴  ┴─┘└─┘ ┴ └─┘

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
[img-codacy]: https://img.shields.io/codacy/grade/254f8db44b004dffa76b8cebfece4c06.svg?style=flat-square
[img-coverage]: https://img.shields.io/codacy/coverage/254f8db44b004dffa76b8cebfece4c06.svg?style=flat-square
[img-release]: https://img.shields.io/github/release/niosus/EasyClangComplete.svg?style=flat-square
[img-downloads]: https://img.shields.io/packagecontrol/dt/EasyClangComplete.svg?maxAge=3600&style=flat-square
[img-downloads-month]: https://img.shields.io/packagecontrol/dm/EasyClangComplete.svg?maxAge=2592000&style=flat-square
[img-subl]: https://img.shields.io/badge/Sublime%20Text-3-green.svg?style=flat-square
[img-mit]: https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square
[img-paypal]: https://img.shields.io/badge/Donate-PayPal-blue.svg?style=flat-square
[img-flattr]: https://img.shields.io/badge/Donate-Flattr-blue.svg?style=flat-square
[img-gitter]: https://badges.gitter.im/niosus/EasyClangComplete.svg?style=flat-square


