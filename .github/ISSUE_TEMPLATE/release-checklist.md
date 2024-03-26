---
name: Release Checklist
about: A checklist of tasks required to make a release
title: release <updated-microservice>-MAJOR.MINOR.PATCH
labels: ''
assignees: ''

---

- [ ] Create a branch for the release
- [ ] Update the dependencies using pip-compile (do not use dependabot)
- [ ] Update the GHCR image tag in `compose.prod.yml` to the imminent release version
- [ ] Bump the `"version"` number in `__init.py__` or relevant file
- [ ] Update the base image version in the Dockerfile if necessary (this should be the most recent LTS version) and do a test build and run of the Docker image on your local machine so you know if something is going to go off the rails before the automated build action on GitHub.
- [ ] Open a PR that merges the release branch into main.
- [ ] Merge the release PR after it passes testing and review.
- [ ] Tag a corresponding release on GitHub. This will trigger an automated Docker image build on GitHub. If the build succeeds it will be automatically published to GHCR. See [wiki](https://github.com/legumeinfo/microservices/wiki/Tagging-Releases-and-Automated-Builds) for details on tagging
