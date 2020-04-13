## Contributing ##
Contributions are welcome! Look at the issue list. If there is something you
think you can tackle, write about it in that issue and submit a Pull Request.

### Follow issue template! ###
Please follow the issue template *exactly* when creating a new issue.
I will be closing issues that do not follow that template. Please understand
that maintaining this codebase takes time and I expect at least well-formatted
issue statement to be able to tackle it. It is very demotivating to format 
the issues instead of actually solving them, so I would really like to outsource this task to the original submitter.

Please don't jump into creating a Pull Request straight away and open an issue
first. This way, we can synchronize our views on the problem, so that everyone
avoids losing time.

### Branches ###
There are two branches:
- `master`: used for ongoing development. Merges into `release` branchright
  before a new release.
- `release`: should be stable and following the last release. Used for urgent
  bug fixing exclusively on top of the previous release.

### Code style ###
- Line width is `80` characters
- Every public function should be documented.
- The code *must* pass linters:
  + `pep8`
  + `pep257`: ignoring `["D209", "D203", "D204", "D213", "D406", "D407"]`

Please ensure, that your code conforms to this.

## Tests ##
Most crucial functionality is covered with unit tests using
[UnitTesting](https://github.com/randy3k/UnitTesting) Sublime Text plugin.

Whenever you contribute new functionality, please make sure it is covered 
by unit tests. It helps to maintain the quality of this software and to 
deal with all complex parts. I will not merge the PRs without unit tests 
covering the new functionality. 
