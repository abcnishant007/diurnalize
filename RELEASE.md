# Release Checklist

This repo is prepared for a PyPI alpha release, but nothing should be uploaded
until CI passes on GitHub.

## Recommended First Release Path

Use PyPI Trusted Publishing through GitHub Actions. This avoids storing a
long-lived PyPI API token in GitHub secrets and creates a verified publishing
link between PyPI and the repository.

1. Push the current `main` branch.

   ```bash
   git push origin main
   ```

2. Confirm the GitHub Actions CI workflow passes on `ubuntu-latest`.

   The workflow runs:

   - tests on Python 3.10, 3.11, and 3.12
   - wheel and sdist builds
   - `twine check`
   - an installed-wheel CLI smoke test
   - synthetic demo data generation with `diurnalize generate-demo`
   - the quick `fit`, `predict`, `validate`, and `report` workflow

3. Bump the package version to an alpha before publishing the first public
   artifact, for example:

   ```toml
   version = "0.1.0a1"
   ```

4. Add a dedicated release workflow, likely `.github/workflows/release.yml`,
   that builds and publishes with `pypa/gh-action-pypi-publish`.

5. In PyPI, configure a pending Trusted Publisher for:

   - PyPI project name: `diurnalize`
   - GitHub owner: `abcnishant007`
   - GitHub repository: `diurnalize`
   - workflow filename: `release.yml`
   - environment: `pypi`

   A pending publisher does not reserve the name until the first successful
   upload, so publish soon after setting it up.

6. Trigger the release workflow. The first successful upload creates the PyPI
   project and captures the `diurnalize` name with a real working alpha package.

## Why Not a Placeholder Package?

Do not upload an empty placeholder solely to reserve the name. PyPI name
retention policy can treat projects with no genuine functionality as name
squatting. This project already has useful functionality, tests, docs, a CLI,
and synthetic demo data generation, so publishing a real alpha is the cleaner
way to claim the name.

## Private Repo Option

The GitHub repo can remain private while the PyPI package is public. PyPI does
not require the source repository to be public.

Tradeoffs:

- Public PyPI users may not be able to access the repository links in package
  metadata.
- A public repo is usually better for trust, issues, and scientific/research
  reuse.
- If the repo stays private for the alpha, either accept private links
  temporarily or remove public repository URLs before publishing.

## API Token Fallback

If Trusted Publishing is not convenient, publish with Twine and a PyPI API
token.

1. Create a PyPI account.
2. Enable two-factor authentication.
3. Create an API token.
4. Build and check locally:

   ```bash
   python -m build
   python -m twine check dist/*
   ```

5. Upload:

   ```bash
   python -m twine upload dist/*
   ```

For a brand-new project, an account-level token may be needed for the first
upload. After the project exists, prefer a project-scoped token or switch to
Trusted Publishing.

## Useful Links

- PyPI Trusted Publishing: https://docs.pypi.org/trusted-publishers/
- Creating a project through OIDC: https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
- Publishing with a Trusted Publisher: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- PyPI name retention policy: https://docs.pypi.org/project-management/name-retention/
