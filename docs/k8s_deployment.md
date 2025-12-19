# Kubernetes deployment

Having wrapped up the project and its dependencies as a Docker image, it's easy to deploy and/or run it using a container-based deployment framework such as Docker Compose or Kubernetes.

In this case, we'll be running it as a one-time Job in a Kubernetes cluster.

## Setting up Kubernetes
To set up a quick and lightweight Minikube-based cluster, follow these steps.
If you're already in a working Kubernetes environment, feel free to skip this.

<details>
  <summary>Click to expand</summary>

Start by installing [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/), the command line tool that you'll need to interact with the K8S cluster and its resources.

```bash
# for debian-based linux x86-64, using apt
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl

curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.28/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.28/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt update
sudo apt install -y kubectl
```

To verify the installation, you can run a quick version check:
```bash
kubectl version --client
```

Now, install [Minikube](https://minikube.sigs.k8s.io/docs/start/), a handy tool to quickly set up a local Docker-based Kubernetes container. Of course, you'll need a working [Docker](https://docs.docker.com/engine/install/ubuntu/) engine.

```bash
# for linux x86-64
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

And spin-up your cluster.
```bash
minikube start
```

If all went well, you'll be able to see the Minikube container by running `docker ps`; as well as its base pods by executing `kubectl get pods -A`.
</details>

## Configuring the Job
This module is designed to run as a one-time operation (instead of a continuously-listening process, like a web server). In Kubernetes terms, this is called a [Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/).

In this project, this Job is configured through the `/tools/k8s/job.yaml` file. There you can specify important fields such as source Docker images, environment variables, resource limits and retry policies.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: mymodule-job
spec:
  template:
    spec:
      restartPolicy: Never  # never retry running the job, even if it fails
      containers:
        - name: mymodule
          image: docker.io/myproject/mymodule:latest  # 1
          imagePullPolicy: Always  # always 
          envFrom:
            - configMapRef:
                name: mymodule-env  # 2
          args: ["--help"]  # pass these arguments to the programs entrypoint (which in this template it's just its CLI)
          resources:
            limits:
              memory: 2000Mi
```

1. The Minikube Kubernetes cluster doesn't have access to your local Docker image storage. You either have to reference an image that is available in a Docker Hub (such as [Harbor](https://harbor.gradiant.org/)); or explicitly get your image inside Minikube following one of [these different approaches](https://minikube.sigs.k8s.io/docs/handbook/pushing/).
2. External configuration in Kubernetes is handled through objects called [ConfigMaps](https://kubernetes.io/es/docs/concepts/configuration/configmap/). Since our project configuration is mainly done through .env files (and manually creating ConfigMaps from .env files it's not very convenient in pure K8S) we rely on the handy ConfigMapGenerator provided by [Kustomize](https://kustomize.io/). This is declared in the `/tools/k8s/kustomization.yaml` file.

Besides the Kubernetes deployment strategy, to set up the project's own configuration start by copying and renaming the provided example, and edit it to your liking:

```bash
cp .env.example tools/k8s/.env
vim tools/k8s/.env
```

## Running the Job
To create the Job, just execute:
```bash
kubectl apply -k tools/k8s
```

To check on the Job and its Pods, run:
```bash
kubectl get jobs

NAME           COMPLETIONS   DURATION   AGE
mymodule-job   1/1           5s         11d
```

```bash
kubectl get pods

NAME                 READY   STATUS      RESTARTS   AGE
mymodule-job-4rn2s   0/1     Completed   0          11d
```