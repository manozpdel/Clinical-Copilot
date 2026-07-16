# Release Process

1. Ensure `main` is green in CI (`ci.yml`, `security.yml`)
2. Update `docs/CHANGELOG.md` with the new version's changes
3. Bump `version` in `pyproject.toml`
4. Tag the release:
```bash
   git tag -a v1.0.0 -m "Clinical Copilot v1.0.0"
   git push origin v1.0.0
```
5. `release.yml` automatically creates a GitHub Release with generated
   notes; `cd.yml` builds and pushes tagged images to GHCR on every
   push to `main`
6. Deploy the new tag:
```bash
   DOCKER_IMAGE_TAG=v1.0.0 bash deployment/scripts/deploy.sh
```
7. Run `bash deployment/scripts/healthcheck.sh` against the deployed
   environment
8. If issues arise, roll back via `deployment/scripts/restore.sh` plus
   redeploying the previous tag