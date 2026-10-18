# Security policy

## Reporting

Use GitHub private vulnerability reporting: the **Security** tab of the
repository, "Report a vulnerability". Do not open a public issue for it.

In scope:

- a build or tool path that writes Elektron bytes into the repository, a PR, an issue or a published artifact;
- a module or tool that can corrupt a card, a project or the unit's flash outside what its README says;
- a CI or workflow weakness (token scope, untrusted input reaching a shell, an unpinned action).

Out of scope: a module that misbehaves on a unit without corrupting data (open a bug report), and behaviour of Elektron's firmware.

## Elektron material

If a report, issue or PR carries an image, slice, `.syx` or firmware dump,
say so privately through the same channel. A maintainer will remove it from
the repository.

## Supported versions

`main` and the images listed in `CHANGELOG.md`. A built image is derived from
the user's own 1.40C and is not distributed.
