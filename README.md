# sample-grpc

[![build](https://img.shields.io/github/actions/workflow/status/nalbam/sample-grpc/push.yml?branch=main&style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/actions/workflows/push.yml)
[![release](https://img.shields.io/github/v/release/nalbam/sample-grpc?style=for-the-badge&logo=github)](https://github.com/nalbam/sample-grpc/releases)

<!-- [![CircleCI](https://circleci.com/gh/nalbam/sample-grpc.svg?style=svg)](https://circleci.com/gh/nalbam/sample-grpc) -->

[![Docker Image Version (latest by date)](https://img.shields.io/docker/v/nalbam/sample-grpc?label=Docker%20Hub&style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)
[![Docker Image Size (latest by date)](https://img.shields.io/docker/image-size/nalbam/sample-grpc?style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)
[![Docker Pulls](https://img.shields.io/docker/pulls/nalbam/sample-grpc?style=for-the-badge&logo=docker)](https://hub.docker.com/r/nalbam/sample-grpc)

<!-- [![DockerHub Badge](http://dockeri.co/image/nalbam/sample-grpc)](https://hub.docker.com/r/nalbam/sample-grpc/) -->

## Docker

```bash
docker pull nalbam/sample-grpc

docker run --rm -p 50051:50051 nalbam/sample-grpc
```

The image uses `python:3.15-slim` (Python 3.15), installs `requirements.txt` and adds
`grpc_health_probe` v0.4.61 for `TARGETARCH`. Set `PORT` to change the listen port:

```bash
docker run --rm -e PORT=50052 -p 50052:50052 nalbam/sample-grpc
```

Build the image locally (`TARGETARCH` is set by BuildKit for the build platform):

```bash
docker build -t sample-grpc .
```

Build both release platforms without publishing (needs QEMU for the non-native platform).
Without `--load` or `--push`, the result stays in the build cache:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t sample-grpc:local .
```

## pip install

Use Python 3.15 (the image version). The dependency versions also support Python 3.10 or later.

```bash
python3.15 -m venv .venv
. .venv/bin/activate
pip install --upgrade -r requirements.txt
pip check

cd src
PORT=50051 python app.py
```

`app.py` is a plain grpcio server. It serves `helloworld.Greeter`, the gRPC health service and server reflection on `[::]:$PORT` (default `50051`) and stops gracefully on `SIGTERM`.

## Test

Start the server, then run the greeter client and the smoke test from another shell.
A new shell does not keep the virtual environment active, so activate it again from
the repository root:

```bash
. .venv/bin/activate
cd src
python greeter_client.py localhost:50051
python smoke_test.py localhost:50051
```

`smoke_test.py` checks that:

- `SayHello` returns `Hello smoke!` and `SayHelloAgain` returns `Hello Again smoke!`.
- The health service returns `SERVING` for the service names `""` and `helloworld.Greeter`.
- Reflection lists `helloworld.Greeter`.

It exits with a non-zero status when a check fails. Without an argument it uses `$TARGET`,
else `localhost:$PORT`, else `localhost:50051`. For a custom port, start the server with
`PORT=50052 python app.py` and run `PORT=50052 python smoke_test.py`.
`greeter_server.py` starts the same server as `app.py`.

## Regenerate protobuf code

```bash
pip install --upgrade -r requirements-dev.txt
pip check

cd src
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto health.proto
git diff --exit-code -- '*_pb2*.py'
```

The command writes all four files: `helloworld_pb2.py`, `helloworld_pb2_grpc.py`,
`health_pb2.py` and `health_pb2_grpc.py`. `git diff` shows no change when the installed
`grpcio-tools` matches the version that generated the committed files (1.85.1).

The generated code sets the minimum runtime versions:

- `*_pb2.py` shows the `protoc` version bundled with `grpcio-tools` (7.35.1 for 1.85.1).
  It runs on any `protobuf` 7.x runtime at that version or later. The runtime does not
  need to equal the header version.
- `*_pb2_grpc.py` sets `GRPC_GENERATED_VERSION` and fails on import with an older `grpcio`.

When you regenerate with a newer `grpcio-tools`, raise the `grpcio` minimum in
`requirements.txt` to that version, and the `protobuf` minimum if the header version is higher.

## Release

Pull requests and pushes to `main` or `master` run the [build workflow](.github/workflows/push.yml).
It publishes nothing, needs no secrets and only has `contents: read`. It:

1. Builds a `linux/amd64` image from the `Dockerfile` (Python 3.15 and `requirements.txt`).
2. Prints the Python, `grpcio*`, `protobuf` and `grpc_health_probe` versions in the image
   and runs `pip check`.
3. Starts one container with the default port `50051` and one with `PORT=50052`. In each
   container it runs `python smoke_test.py localhost:<port>` and
   `grpc_health_probe -addr=localhost:<port>`. On failure it prints the container logs.
4. Builds a `linux/arm64` image without pushing it. The arm64 image is not started,
   because the runner is amd64.

Branch pushes only run this check. Release a version by pushing a `v*` SemVer tag
such as `v0.11.0` or `v0.11.0-rc.1`. Tags must fit Docker's 128-character limit
and omit `+build` metadata, so the Git, image and deployment versions stay identical.
Leading zeros such as `v01.0.0` are rejected.

Release only a commit that the build workflow passed on `main`. `gh run view --exit-status`
also exits 0 while a run is queued or in progress, so check `status` and `conclusion`:

```bash
export sha=<full commit SHA on main>
gh run list --workflow push.yml --branch main --commit "$sha" \
  --json databaseId,status,conclusion,headSha
gh run view <databaseId> --json headSha,status,conclusion --jq \
  'if .headSha == env.sha and .status == "completed" and .conclusion == "success"
   then "ok" else error("run is not a completed success for \(env.sha)") end'
```

Continue only when the command prints `ok`. It fails when the run is for another
commit, is not `completed`, or has a `conclusion` other than `success`. Then tag the commit:

```bash
git tag v0.11.0 "$sha"
git push origin v0.11.0
```

The [release workflow](.github/workflows/release.yml) runs the same build check, then:

1. Validates the tag, then builds and pushes `nalbam/sample-grpc:<tag>` (for example
   `nalbam/sample-grpc:v0.11.0`) for `linux/amd64` and `linux/arm64`. The `Dockerfile`
   downloads `grpc_health_probe` for each `TARGETARCH`. Stable versions also update
   `latest`; prereleases only publish their version tag.
2. Creates a GitHub Release with commit notes since the previous reachable version
   tag, excluding merge commits and `chore: release` commits. Tags with a prerelease
   suffix create GitHub prereleases. A rerun updates the existing release.
3. Sends a `gitops` repository dispatch to `opspresso/argocd-env-demo` with
   `username=nalbam`, `project=sample-grpc`, `version=<tag>`, `container=app`,
   `phase=alpha` and `type=helm`.
4. For stable tags only, sends the same payload with `phase=prod` and `auto_merge=true`
   through the GitHub `prod` environment. Prereleases stop at alpha.

Each stage runs only after the previous stage succeeds. Release runs are serialized,
also across tags, because they share `latest` and the deployment targets.
A successful dispatch only requests a deployment. It does not confirm that the
alpha or prod rollout has completed; check Argo CD for that. The prod job does not
wait for the alpha rollout.

Repository settings:

- Secrets `DOCKER_USERNAME` and `DOCKER_PASSWORD`: a Docker Hub account and token
  that can push `nalbam/sample-grpc`. Only the image job uses them.
- Secret `GHP_TOKEN`: a token that can create repository dispatches on
  `opspresso/argocd-env-demo` (fine-grained: Contents read and write).
- Environment `prod` (Settings > Environments). To require manual approval before
  production, add required reviewers to it. Without reviewers, prod runs right after alpha.
- The workflow `GITHUB_TOKEN` has `contents: read` by default and `contents: write`
  only in the GitHub Release job.

After a release, check each result against the same tag and commit:

```bash
tag=v0.11.0
export sha=$(git rev-list -n 1 "$tag")       # must be the chosen commit
gh run list --workflow release.yml --branch "$tag" \
  --json databaseId,status,conclusion,headSha
gh run view <databaseId> --json headSha,status,conclusion --jq \
  'if .headSha == env.sha and .status == "completed" and .conclusion == "success"
   then "ok" else error("run is not a completed success for \(env.sha)") end'
gh run view <databaseId> --json jobs --jq '.jobs[] | [.name, .status, .conclusion] | @tsv'
gh release view "$tag" --json tagName,isPrerelease,url
docker buildx imagetools inspect "nalbam/sample-grpc:$tag"   # lists linux/amd64 and linux/arm64

docker run -d --name sample-grpc-check "nalbam/sample-grpc:$tag"
docker exec sample-grpc-check python smoke_test.py localhost:50051
docker exec sample-grpc-check grpc_health_probe -addr=localhost:50051
docker rm -f sample-grpc-check
```

Treat the release as complete only when the run check prints `ok` and the other
checks match the tag. A run that waits for `prod` approval is not `completed` and
fails the check. The job list shows each stage; for a prerelease the prod job is `skipped`.

`docker run` pulls the image for the host platform. To check the other platform, add
`--platform linux/arm64` or `--platform linux/amd64` (QEMU is needed for a non-native platform).

Git tags are the release version source. The `VERSION` and `BUMP` files are not
read or updated by these workflows.
