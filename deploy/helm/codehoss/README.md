# CodeHoss Helm chart

Runs a self-hosted CodeHoss on Kubernetes (1.29 or newer).

## What it creates

One pod with:

| Container | What it does |
|---|---|
| `seed-content` (init) | copies the courses from the image onto the content volume (first start only, by default) |
| `docker` (native sidecar) | a private **privileged** Docker engine (`docker:dind`) that runs every learner sandbox, notebook kernel and lab; reachable only through a unix socket inside the pod |
| `build-images` (init) | `dojo build-images`: the sandbox images, cached on the docker volume |
| `server` | CodeHoss itself (API, browser app) on port 8000 |

Plus a Service, an optional Ingress, a Secret (the key that encrypts learners' saved API
keys), PersistentVolumeClaims for data, sandbox images and content, and optionally an
Ollama server for AI lessons and the tutor.

It's one replica on purpose: progress is in SQLite and sandbox sessions live in the pod.

## Install

Build the image from the repo root and push it where your cluster can pull it, for
example your GitLab project's container registry:

```bash
docker build -t registry.gitlab.com/<you>/codehoss:0.3.0 .
docker push registry.gitlab.com/<you>/codehoss:0.3.0

helm install dojo deploy/helm/codehoss -n dojo --create-namespace \
  --set image.repository=registry.gitlab.com/<you>/codehoss --set image.tag=0.3.0 \
  --set authors=<your-username> \
  --set ingress.enabled=true --set ingress.host=dojo.example.com
```

The first start builds the sandbox images (several minutes; follow it with
`kubectl -n dojo logs deploy/dojo-codehoss -c build-images -f`). Later starts reuse them.
To start faster, build only some courses' images: `--set 'sandbox.buildModules={programming-basics,python-basics}'`.

## Values worth knowing

| Value | Default | |
|---|---|---|
| `authors` | `""` | usernames allowed in the Studio (`*` for everyone); off when empty. With `--set`, escape commas: `--set 'authors=ada\,bob'` |
| `sandbox.buildModules` | `[]` | courses to build images for (empty: all) |
| `content.seed` | `ifEmpty` | `always` picks up a new image's courses but overwrites Studio edits |
| `persistence.docker.size` | `40Gi` | sandbox images; labs add k3s and registry images |
| `ollama.enabled` | `false` | run Ollama in the cluster (or point `ai.ollamaUrl` at one) |
| `secretKey` / `existingSecret` | generated | kept across upgrades and after uninstall |
| `sandbox.labRuntime` | `""` | e.g. `sysbox-runc` to run lab engines unprivileged |
| `dind.mtu` | pod's own | MTU of the engine's networks; the default follows the pod network, which overlays often set below 1500 (Docker's 1500 would silently drop large packets, e.g. TLS downloads during image builds) |

See [values.yaml](values.yaml) for everything.

## Security

The Docker engine must be privileged (it runs containers, and labs run Docker and k3s
inside those). Learner code never runs in it directly: each sandbox is a locked-down
container (no network, no capabilities, read-only filesystem, memory/CPU/pids limits).
Still, give CodeHoss its own namespace, schedule it on nodes you trust, and expose only
the Service. Uninstalling keeps the data and content volumes and the Secret
(`helm.sh/resource-policy: keep`); delete them to remove learners' accounts and work.

## Tested

Installed into k3s v1.37 (running in Docker, flannel MTU 1450), building the Python Basics
and Data Science images in the pod. Checked: learners register; code runs in sandboxes,
which have no network; datasets are mounted at `/data`; exercises are graded; the skill
map and the Studio work. A pod restart is ready in under 20 s (cached images) and keeps
accounts. `helm upgrade` keeps the secret key; `helm uninstall` keeps the data and content
volumes and the key, and a reinstall picks them up (accounts still log in). The engine
listens only on its pod-local socket.
