# Run RKO on an instance

## Terminal command

After `uv sync --locked --group dev`, run from the repository root:

```bash
uv run --locked rko src/rko/examples/instances/kp50.txt \
  --limit-time 10 --backend process --random-state 42 \
  --output-csv results/kp50.csv
```

This is the Knapsack adapter shipped with the library, analogous to the supplied
C++ `Problem.h`. It reads the instance, constructs `RKO`, runs the configured
portfolio, prints cost/profit/weight/feasibility and exports CSV. Use quotes around
paths containing spaces. In PowerShell put the command on one line or replace
Bash continuation backslashes with PowerShell backticks.

`uv run --locked rko --help` lists options. The equivalent installed command is
`rko ...`; running the Python module directly also remains supported. Startup
is additional to the process search budget; see README for stopping limits.
Defaults currently select ten algorithms/workers, which may oversubscribe a
small machine. Use an explicit smaller portfolio as below rather than assuming
`--n-jobs 4` schedules the default ten.

## Your configuration directory

`--params-dir` selects a directory, not a single file. It must contain
`config.toml` and the selected algorithms' parameter TOMLs. To copy the packaged
parameters without depending on source paths, run this once:

```bash
uv run --locked python -c "import shutil; from rko.parameters.loader import default_params_dir; shutil.copytree(default_params_dir(), 'configs/my-run', ignore=shutil.ignore_patterns('*.py', '__pycache__'))"
```

This refuses to overwrite an existing directory. Edit
`configs/my-run/config.toml`, for example:

```toml
[run]
control = 1
pool_size = 10

[active_metaheuristics]
list = ["SA", "BRKGA", "GA", "PSO"]
```

Then run:

```bash
uv run --locked rko path/to/instance.txt \
  --params-dir configs/my-run --limit-time 60 \
  --backend process --n-jobs 4 --random-state 42 \
  --output-csv results/my-instance.csv
```

Each algorithm's `.toml` contains `[offline]` scalar values and `[online]` named
value grids. `control = 0` selects offline settings; `control = 1` enables online
control for algorithms that implement it. SA's reference adaptive path remains
[open compatibility work](cpp-compatibility.md).

Do not edit installed package files. Do not copy C++ `config_tests.conf`,
`ParametersOffline.txt` or `ParametersOnline.txt` directly: their formats are not
TOML. C++ `strategy`, `restart`, `MAXRUNS` and `debug` are not currently supported
Python run settings; unsupported keys are rejected, not silently honored.
Repeat the command for separate trials. Current constraints are in
[status.md](status.md).

## Instance format

The current terminal adapter expects integer Knapsack data: item count and
capacity, followed by one profit/weight pair per item, separated by whitespace.
For example, an instance with three items and capacity five:

```text
3 5
6 1
10 2
12 3
```

There is no implicit parsing of arbitrary optimization instances. For a different
problem, provide its reader, random-key decoder and objective through the Python
`RKO` class, corresponding to adapting `Problem.h` in C++. A generic problem-plugin
terminal interface is not implemented by this command.

## Existing batch selection

Omit the positional instance to run a directory/glob selection:

```bash
uv run --locked rko --instances-dir path/to/instances --pattern "kp*.txt" \
  --params-dir configs/my-run --limit-time 60 --n-jobs 4 \
  --output-csv results/batch.csv
```

A single positional instance cannot be combined with batch selectors. Without
any selectors, the bundled `kp10.txt` and `kp50.txt` references are used. Results
are written below the caller's `results/` directory unless `--output-csv` selects
a different path. Generated result directories are ignored by Git.
