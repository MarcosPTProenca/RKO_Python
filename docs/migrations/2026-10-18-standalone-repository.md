# Standalone RKO Python repository

## Decision and layout

The owner requested that RKO stop living inside the agent project's nested
folders and approved migration into `MarcosPTProenca/RKO_Python` while leaving
`RKO-Agent` intact. The canonical checkout is now
`C:\Users\Marcos\Documents\RKO_Python`, branch `main`.

```text
RKO_Python/
  pyproject.toml
  uv.lock
  README.md
  LICENSE
  AGENTS.md
  .github/workflows/ci.yml
  src/rko/
  tools/
  docs/
```

There is no enclosing `rko_agent` directory or runtime dependency on the agent
checkout. Tests remain under `src/rko/tests`, are excluded from installed wheels,
and run from this root. Bundled fixtures and configuration remain package data.

## Provenance and history

Imported the committed `rko_agent/` tree from `MarcosPTProenca/RKO-Agent`,
revision `1066171f238c3820dfc315e6412e3526356b4e40`, plus its repository-root CI.
Uncommitted files, environments, generated results and unrelated agent files were
not imported. The source checkout, branch, remotes and working changes were not
modified.

The migration merge has both the previous RKO_Python main and the exact source
commit as parents. No squash, force push or history rewriting is required;
original commit identifiers in audit documents remain resolvable. Only the
current tree is flattened, so older commits still show their historical paths.
The previous RKO_Python snapshot is additionally preserved in the published tag
`archive/pre-standalone-migration-2026-10-18` at
`9240994` (the pre-migration main). Use a separate worktree to inspect it safely:

```bash
git worktree add --detach ../RKO_Python-legacy \
  archive/pre-standalone-migration-2026-10-18
```

To roll back main, make a normal reviewed revert of the migration merge rather
than resetting or force-pushing shared history. Historical audit/planning files
retain their original paths and findings; consult their commit context and the
current README instead of treating those old paths as current commands.

## Packaging and compatibility

Retain the destination's distribution name `rko`; replace the imported
`rko-agent` identity and regenerate `uv.lock`. Version `0.3.0.dev0` denotes an
unreleased development line. No artifact is published to PyPI by this migration.
CI now runs at the repository root on Ubuntu and Windows, including isolated
wheel/sdist execution. Repository/issue URLs point to this standalone repository.

This imports the new `from rko import RKO` class API and requires Python 3.14+;
it is not a drop-in update of the destination's former Python 3.8+/0.2.1 API.
The functional `rko.run` adapter only preserves the imported implementation's
legacy contract. It does not promise compatibility with every previous API from
the destination repository. This migration does not fix the remaining RNG,
scheduler, parity, scientific-quality or documentation audit gates.

## Validation

- Ruff lint and formatting: passed for all 59 Python files.
- Full regression suite: 183 passed in 124.53 seconds.
- Wheel and sdist builds: passed; isolated installs both executed real serial
  and spawned RKO solves successfully, including bundled resources.
- Staged `src/` tree object equals the source commit's `rko_agent/src/` exactly:
  this migration changes no solver, parameter, fixture or test content.
- The preserved destination license matches its archived bytes exactly.
- The imported pre-commit Ruff 0.11.13 disagreed with the locked Ruff 0.15.7
  (UP038). Pin both development and pre-commit to 0.15.7; both hooks now pass.
- CI no longer has an agent-relative working directory. Native Windows execution
  remains covered by the copied Ubuntu/Windows artifact-validation matrix.

## Attribution and licensing

The destination's existing Apache-2.0 `LICENSE` is preserved byte-for-byte;
its metadata had inconsistently advertised MIT. This migration does not invent
new authorship, replace that license or declare that imported work was relicensed.
The destination's previous project metadata credited Felipe Silvestre Cardoso
Roberto and João Assaoka; their historical contributions remain in Git history
and in the archive tag. Imported source authorship remains in its original
history. The bundled reference fixtures retain their separate upstream MIT
license and provenance under `src/rko/examples/instances`.

The owner must confirm appropriate licensing/attribution for the combined
implementation before a release. Keeping the historical license file is not a
legal ownership audit or proof that all imported code is covered by it.
