# Contributing to Flavor

We love your input! We want to make contributing to Flavor as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## We Develop with Github
We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## We Use [Github Flow](https://guides.github.com/introduction/flow/index.html)
Pull requests are the best way to propose changes to the codebase:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any contributions you make will be under the Apache 2.0 Software License
In short, when you submit code changes, your submissions are understood to be under the same [Apache 2.0 License](LICENSE) that covers the project.

## Report bugs using Github's [issues](https://github.com/provide-io/flavor/issues)
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/provide-io/flavor/issues/new).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Process

1. Clone the repository
```bash
git clone https://github.com/provide-io/flavor.git
cd flavor
```

2. Set up your development environment
```bash
source env.sh  # This sets up the virtual environment
```

3. Run tests to ensure everything works
```bash
pytest
```

4. Make your changes and add tests

5. Run the test suite
```bash
pytest -v
```

6. Check code style
```bash
ruff check src/
ruff format src/
mypy src/
```

## License
By contributing, you agree that your contributions will be licensed under its Apache 2.0 License.

## References
This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/master/CONTRIBUTING.md)