# Completing the includes <small>(exprerimental)</small>

The plugin has an experimental capability to complete includes. Currently, the automatic completion after typing `#include <` will not work due to a way brackets get auto-matched by Sublime Text (read more about it [here](https://forum.sublimetext.com/t/completion-triggers/13139/5)). 

However, when using <kbd>Alt</kbd>+<kbd>/</kbd> on Linux and <kbd>Ctrl</kbd>+<kbd>Space</kbd> on Windows and macOS after `<` symbol while typing `#include <` the plugin will walk the tree starting at the current include folders (read more about where these come from [here](../configs)) to generate a list of potential includes that it will show momentarily.

This is still experimental and can be a bit slow. Also, the number of includes is limited by approx. 4 million entries.
