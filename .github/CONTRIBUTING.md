<!-- derived from https://github.com/github/docs/blob/main/CONTRIBUTING.md -->
# Contributing <!-- omit in toc -->

Thank you for investing your time in contributing to our project!

Read our [Code of Conduct](./CODE_OF_CONDUCT.md) to keep our community approachable and respectable.

In this guide you will get an overview of the contribution workflow from opening an issue, creating a PR, reviewing, and merging the PR.

## New contributor guide

To get an overview of the project, read the [README](README.md).

## Getting started

The following are instructions on the different ways you may contribute to the project.

### Issues

#### Create a new issue

If you spot a problem with the microservices, [search if an issue already exists](https://docs.github.com/en/github/searching-for-information-on-github/searching-on-github/searching-issues-and-pull-requests#search-by-the-title-body-or-comments). If a related issue doesn't exist, you can open a new issue. 

#### Solve an issue

Scan through our [existing issues](https://github.com/github/microservices/issues) to find one that interests you. You can narrow down the search using `labels` as filters.

### Make Changes

#### Make changes locally

1. Fork the repository.
- Using GitHub Desktop:
  - [Getting started with GitHub Desktop](https://docs.github.com/en/desktop/installing-and-configuring-github-desktop/getting-started-with-github-desktop) will guide you through setting up Desktop.
  - Once Desktop is set up, you can use it to [fork the repo](https://docs.github.com/en/desktop/contributing-and-collaborating-using-github-desktop/cloning-and-forking-repositories-from-github-desktop)!

- Using the command line:
  - [Fork the repo](https://docs.github.com/en/github/getting-started-with-github/fork-a-repo#fork-an-example-repository) so that you can make your changes without affecting the original project until you're ready to merge them.
2.  Follow the instructions for how to setup and run the specific microservice(s) you want to change (see each microservice's directory for details)
3.  Create a working branch and start making changes!

### Commit your changes

The repository uses pre-commit hooks to style and lint the code. Specifically, we use the [pre-commit framework](https://pre-commit.com/). Make sure you have that installed on your machine before proceeding.

Once you have pre-commit installed, setup our pre-commit hooks by running the following command in the root of the repository:
```console
pre-commit install
```

Now you can commit your changes. This will automatically run the pre-commit hooks. If there are errors, some may be fixed automatically but others may require manual intervention. If any errors require intervention, the commit will fail and you will need to fix the errors before trying to commit again. When committing after fixing errors you can use the same commit message as the previous commit because the previous commit failed and therefore wasn't added to the commit log.

### Pull Request

When you're finished with the changes, create a pull request, also known as a PR.
- Don't forget to [link the PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue) if you are solving one.
- Enable the checkbox to [allow maintainer edits](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/allowing-changes-to-a-pull-request-branch-created-from-a-fork) so the branch can be updated for a merge.
Once you submit your PR, a team member will review your proposal. We may ask questions or request additional information.
- We may ask for changes to be made before a PR can be merged, either using [suggested changes](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/incorporating-feedback-in-your-pull-request) or pull request comments. You can apply suggested changes directly through the UI. You can make any other changes in your fork, then commit them to your branch.
- As you update your PR and apply changes, mark each conversation as [resolved](https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/commenting-on-a-pull-request#resolving-conversations).
- If you run into any merge issues, checkout this [git tutorial](https://github.com/skills/resolve-merge-conflicts) to help you resolve merge conflicts and other issues.

### Your PR is merged!

Congratulations :tada::tada: We thank you for your contribution :sparkles:.
