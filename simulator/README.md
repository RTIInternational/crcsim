# CRC model simulator

`crcsim` is a Python package implementing the CRC screening model simulation. This package isn't expected to be deployed and executed on its own. Instead, it's expected to be installed as a dependency of an experiment.

## Documentation

See [docs/design.md](./docs/design.md) for a discussion of the package's design.

## Development

### Getting started

To set up a Python development environment for `crcsim`:

1. From the repo root, `cd simulator`.
1. Create a Python virtual environment based on Python 3.6. (Currently, support is limited to Python 3.6, because that is the version installed on the RTI Cluster, which is where we expect to deploy and run the experiments.)
1. Activate the virtual environment.
1. Install development dependencies with `pip install -r requirements.txt`.
1. Install `crcsim` with `pip install -e .`. The `-e` option specifies "development" mode, meaning that any changes you make to the code are recognized immediately without having to reinstall the package.

Note that although a Docker setup is provided, it's designed to be used only for continuous integration and not for day-to-day development.

### Running tests

Tests are run automatically as part of GitLab's continuous integration process using Docker. However, you can also run them locally with `./run_tests.sh`, or you can mimic the CI process by running them in Docker with:

 ```
$ docker-compose build
$ docker-compose run --rm sim ./run_tests.sh
 ```

The tests include unit/integration testing as well as formatting and linting.

### Pre-commit hooks

A [pre-commit](https://pre-commit.com) configuration is provided for running some of the tests automatically before every commit. (The unit/integration tests are excluded, because they might be slow.)

Enabling this is optional but encouraged because it's more convenient than remembering to do it manually. To enable, run `pre-commit install` inside your activated virtual environment. After that, you will be prevented from committing your changes if any of the tests fail. If for some reason you really need to commit changes despite failing checks, run `git commit --no-verify`.

**NOTE:** The pre-commit hooks might fail to run if you're trying to commit files from the `simulator` directory while a different virtual environment is activated. For example, perhaps you've activated the data-prep virtual environment or one of the experiments' virtual environments. It's a somewhat unlikely scenario but good to be aware of. If this happens, you should activate your simulator virtual environment and try committing again.

### Managing dependencies

Because `crcsim` is a package intended to be installed by other applications (namely our model experiments), its own dependencies defined in `setup.py` should be as unconstrained as possible. The other applications are responsible for pinning package versions when using `crcsim`.

For the purposes of developing `crcsim` and running its tests, though, we pin all our dependencies in `requirements.txt` to ensure consistent environments across developers and platforms. We use [pip-tools](https://github.com/jazzband/pip-tools) for managing `requirements.txt`. Below is a quick reference for common use cases.

To add or remove a package dependency :

1. Edit [simulator/requirements.in](./requirements.in). If the dependency is a package dependency (that is, a dependency needed for installing and using `crcsim` and not simply for development and testing), **additionally** edit the `install_requires` section in [setup.py](./setup.py).
1. Run `pip-compile` to generate a new version of [requirements.txt](./requirements.txt).
1. Run `pip-sync` to apply any changes to your virtual environment.
1. Re-install `crcsim` into your virtual environment with `pip install -e .` (because `pip-sync` uninstalls it).
1. If you use the Docker environment, run `docker-compose build` to rebuild your image.

To upgrade a dependency:

1. Run `pip-compile --upgrade-package <pkgname>` to generate a new version of [requirements.txt](./requirements.txt).
1. Run `pip-sync` to apply any changes to your virtual environment.
1. Re-install `crcsim` into your virtual environment with `pip install -e .` (because `pip-sync` uninstalls it).
1. If you use the Docker environment, run `docker-compose build` to rebuild your image.

## Running experiments

An experiment uses the `crcsim` package to test a hypothesis by comparing results under different parameter values. We haven't completely settled on the location where we'll store our experiments, so for now you may find them in one of two locations:

- In a subdirectory of the [experiments/](./experiments) directory, committed to the `main` repo branch.
- In the [simulator/crcsim/experiment/] directory, committed to a branch named `exp-{experiment_name}`.

See the READMEs in those locations for details on any specific experiment.
