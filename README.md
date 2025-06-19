# CRC model simulator

The colorectal cancer (CRC) screening model is designed to examine the impacts of screening strategies and patient compliance on CRC outcomes like mortality rate.

`crcsim` is a Python package implementing the CRC screening model simulation. This package isn't expected to be deployed and executed on its own. Instead, it's expected to be installed as a dependency of an experiment.

## Documentation

See [docs/design.md](./docs/design.md) for a discussion of the package's design.

## Development

### Getting started

To set up a Python development environment for `crcsim`:

1. [Install uv](https://docs.astral.sh/uv/getting-started/installation/).
1. Run `uv sync --dev` to create a virtual environment and install the project.
1. Run `. .venv/bin/activate` to activate the virtual environment. (It's helpful to alias this command to something easier to remember like `activate`.)

### Unit tests

Tests are run automatically as a GitHub Action when a PR is created or updated. You can also run them locally with the command `uv run pytest`. 

Unit tests must be added for all new model functionality.

### Linting and formatting

`crcsim` uses `ruff` for linting and formatting. All files are checked with a GitHub Action when a PR is created or updated.

To run `ruff` locally, you can use the commands `uv run ruff check .` (for linting) and `uv run ruff format --check .` (for formatting and import sorting).

If you're using VS Code, you can edit your settings to format on save with `ruff`. Here's an example `.vscode/settings.json` for this project. This automatically formats on save, but doesn't sort imports or lint on save. If you want to do those too, you can change the values in `"editor.codeActionsOnSave"` to `true`. 

```
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": "explicit",
            "source.organizeImports": "explicit"
        },
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "ruff.configuration": "./pyproject.toml",
    "jupyter.notebookFileRoot": "${workspaceFolder}",
}
```

### Pre-commit hooks

A [pre-commit](https://pre-commit.com) configuration is provided for running linting, formatting, import sorting, and type checking automatically before every commit. (The unit/integration tests are excluded, because they might be slow.)

Enabling this is optional but encouraged because it's more convenient than remembering to do it manually. To enable, run `pre-commit install` inside your activated virtual environment. After that, you will be prevented from committing your changes if any of the tests fail. If for some reason you really need to commit changes despite failing checks, run `git commit --no-verify`.

### Managing dependencies

Because `crcsim` is a package intended to be installed by other applications (namely our model experiments), its own dependencies defined in `pyproject.toml` should be as unconstrained as possible. The other applications are responsible for pinning package versions when using `crcsim`.

For the purposes of developing `crcsim` and running its tests, we use `uv` to manage dependencies. Below is a quick reference for common use cases.

- To add a package dependency: `uv add my-dependency`
- To remove a package dependency: `uv remove my-dependency`
- To add/remove a development dependency (a package that is necessary for development but not necessary to install `crcsim`, eg, `pytest`): `uv add/remove --dev my-dependency`
- To upgrade a dependency: `uv add my-dependency --upgrade`

## Running experiments

An experiment uses the `crcsim` package to test a hypothesis by comparing results under different parameter values. Experiments are stored as branches named `exp-{experiment_name}`. Experiment files are stored in the `crcsim/experiment/` directory.

To run an experiment, check out the experiment branch and follow instructions in `crcsim/experiment/README.md`. 

To create a new experiment, check out a new branch and edit/add files in `crcsim/experiment/` as needed.

By default, experiements should not be merged into `main`. We may merge an experiment into `main` to make a release tied to a paper.
