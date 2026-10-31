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

Build the image locally (`TARGETARCH` is set by BuildKit for the build platform):

```bash
docker build -t sample-grpc .
```

## pip install

```bash
pip3 install --upgrade -r requirements.txt

cd src
PORT=50051 python3 app.py
```

`app.py` is a plain grpcio server. It serves `helloworld.Greeter`, the gRPC health service and server reflection on `[::]:$PORT` (default `50051`) and stops gracefully on `SIGTERM`.

## Test

Start the server, then run the greeter client and the smoke test from another shell:

```bash
cd src
python3 greeter_client.py localhost:50051
python3 smoke_test.py localhost:50051
```

`smoke_test.py` calls the Greeter, the health service (service name `""`) and reflection (`helloworld.Greeter` must be listed). `greeter_server.py` starts the same server as `app.py`.

## Regenerate protobuf code

```bash
pip3 install -r requirements-dev.txt

cd src
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto health.proto
```

The generated `*_pb2.py` header shows the `protoc` version bundled with `grpcio-tools`, which can be older than the installed `protobuf` runtime.

## Release

Pull requests and pushes to `main` or `master` run the [build workflow](.github/workflows/push.yml).
It builds a `linux/amd64` image from the `Dockerfile` (Python 3.14 and `requirements.txt`),
starts the container on port `50051`, then runs `python smoke_test.py localhost:50051`
(Greeter, health, reflection) and `grpc_health_probe -addr=localhost:50051` in the container.
On failure it prints the container logs. It needs no secrets and only `contents: read`.

Branch pushes only run this check. Release a version by pushing a `v*` SemVer tag
such as `v0.11.0` or `v0.11.0-rc.1`. Tags must fit Docker's 128-character limit
and omit `+build` metadata, so the Git, image and deployment versions stay identical.
Leading zeros such as `v01.0.0` are rejected.

```bash
git tag v0.11.0
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

Git tags are the release version source. The `VERSION` and `BUMP` files are not
read or updated by these workflows.
