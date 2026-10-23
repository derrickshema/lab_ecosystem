# labcore

Shared Python code for the ecosystem's backends. Currently: database engine and session helpers (`labcore.db`).

## Installing into an app

From an app's `backend/` folder, with its `.venv` activated:

```sh
pip install -e ../../../packages/labcore
```

`-e` (editable) links the venv to this folder instead of copying it, so edits here apply to every app immediately.

**Don't put labcore in `requirements.txt`.** `pip freeze` will list it as `labcore @ file:///C:/Users/...`, an absolute path that only works on your machine. Delete that line after freezing. Docker installs labcore separately (see each app's `Dockerfile`).

## Docker

App images are built with the **repo root** as the build context, so the Dockerfile can copy both `packages/labcore` and the app. The root `.dockerignore` controls what gets sent. In development, compose mounts this folder into the container, so edits here hot-reload there too.
