# Releasing

`.github/workflows/release.yml` runs on `v*` tags: it checks the tag matches
`src/permio/_version.py`, runs the tests, builds the sdist and wheel and
publishes them to PyPI with [trusted publishing](https://docs.pypi.org/trusted-publishers/)
(no API token). The trusted publisher is registered on PyPI for the project
`permio` (owner `perms-io`, repository `permio-python`, workflow
`release.yml`, environment `pypi`), so pushing a tag that matches the version
is all a release needs. Every CI job runs on Blacksmith except the publish step,
which runs on a GitHub-hosted runner because `pypa/gh-action-pypi-publish` only
supports self-hosted runners on a best-effort basis.
