# Оператор OpenRAG

Kubernetes-оператор, который управляет развёртываниями OpenRAG через единый пользовательский ресурс `OpenRAG`.
Он создаёт и владеет развёртываниями фронтенда, бэкенда и Langflow, сервисами и сервисными аккаунтами.
Внешние зависимости (OpenSearch, Docling) задаются через конфигурацию подключения — этот оператор их не развёртывает.

## Предварительные требования

- Go 1.26.0 (`gvm use go1.26.0`)
- kubectl, указывающий на кластер
- Helm 3.x (для установки через Helm-чарт)

## Установка

### Вариант 1: использование Helm (рекомендуется)

Helm-чарт развёртывает как CRD, так и развёртывание оператора.

```bash
# Установка из локального чарта
helm install openrag-operator ./kubernetes/helm/operator \
  --namespace openrag-control \
  --create-namespace

# Проверка установки
kubectl get deployment -n openrag-control
kubectl get crd openrags.openr.ag
```

**Настройка установки:**

```bash
# Задать пользовательский тег образа
helm install openrag-operator ./kubernetes/helm/operator \
  --namespace openrag-control \
  --create-namespace \
  --set image.tag=v0.1.0

# Или использовать файл значений
helm install openrag-operator ./kubernetes/helm/operator \
  --namespace openrag-control \
  --create-namespace \
  -f my-values.yaml
```

### Вариант 2: использование kubectl + kustomize

```bash
# Установка CRD
make install

# Развёртывание оператора
make deploy IMG=ghcr.io/langflow-ai/openrag-operator:latest
```

### Вариант 3: локальная разработка (см. ниже)

## Локальный кластер разработки (kind + podman)

### 1. Запустите машину podman

```bash
podman machine start
```

### 2. Настройте kind на использование podman

```bash
export KIND_EXPERIMENTAL_PROVIDER=podman
```

Добавьте это в ваш профиль оболочки (`~/.zshrc` или `~/.bashrc`), чтобы сделать настройку постоянной.

### 3. Создайте кластер

```bash
kind create cluster --name openrag
```

Проверьте, что он запущен:

```bash
kubectl cluster-info --context kind-openrag
kubectl get nodes
```

### 3a. Запустите машину podman, если она не запущена после перезагрузки ноутбука
```bash
podman start openrag-control-plane
kubectl config use-context kind-openrag  
```

### 4. Загрузите локально собранный образ оператора (необязательно)

Если вы собрали образ локально вместо подтягивания из GHCR:

```bash
make docker-build IMG=openrag-operator:dev
podman save openrag-operator:dev | kind load image-archive /dev/stdin --name openrag
```

Установите CRD

```bash
make install
```

Запустите оператор локально:

```bash
make run
```

Примените пример CR (сначала создайте namespace; оператор не создаёт его, когда `metadata.namespace` равен `targetNamespace`):

```bash
kubectl create namespace my-tenant
# Кластеры kind/Colima обычно имеют только 2 CPU — используйте пример kind-local:
kubectl apply -f config/samples/openrag_v1alpha1_openrag-kind-local.yaml
kubectl get pods -n my-tenant
```

На узле kind с 2 CPU пример по умолчанию (`openrag_v1alpha1_openrag.yaml`) запрашивает 1500m CPU для фронтенда+бэкенда+langflow, и langflow останется в состоянии `Pending` с ошибкой `Insufficient cpu`.

### Сборка образов приложения локально и их использование в kind (Colima/Docker)

Из **корня репозитория** (не из `kubernetes/operator/`):

```bash
# Соберите backend, frontend, langflow и загрузите их в узел kind
make kind-build-load-apps

# В другом терминале: оператор + CR (kind-local задаёт imagePullPolicy: Never)
cd kubernetes/operator
make install
make run

kubectl create namespace my-tenant
kubectl apply -f config/samples/openrag_v1alpha1_openrag-kind-local.yaml
```

Образы тегируются так же, как в апстриме (`langflowai/openrag-*:latest`), поэтому примеру kind-local не нужны собственные имена. `imagePullPolicy: Never` заставляет кластер использовать копии, загруженные через `kind load docker-image`.

После изменения кода и пересборки:

```bash
make kind-build-load-apps   # или соберите только изменённое, затем make kind-load-app-images
kubectl rollout restart deployment -n my-tenant openrag-fe openrag-be openrag-lf
```

Необязательно: соберите/загрузите образ **оператора** тем же способом:

```bash
cd kubernetes/operator
make docker-build IMG=openrag-operator:dev
kind load docker-image openrag-operator:dev --name openrag
make deploy IMG=openrag-operator:dev   # вместо make run
```

### 5. Выключение

```bash
kind delete cluster --name openrag
```

## Быстрый старт (разработка)

```bash
make deps          # скачать controller-gen, kustomize, envtest в ./bin
make manifests     # перегенерировать YAML CRD + RBAC (запускать после редактирования типов)
make generate      # перегенерировать методы DeepCopy (запускать после редактирования типов)
make build         # скомпилировать bin/manager
make install       # установить CRD в текущий кластер
make deploy IMG=ghcr.io/langflow-ai/openrag-operator:latest
```

Примените пример CR:

```bash
kubectl apply -f config/samples/openrag_v1alpha1_openrag.yaml
kubectl get openrag
```

## Helm-чарт

Helm-чарт оператора находится в `kubernetes/helm/operator/` со следующей структурой:

```
kubernetes/helm/operator/
├── Chart.yaml                     # Метаданные чарта
├── values.yaml                    # Значения конфигурации по умолчанию
├── .helmignore                    # Файлы, игнорируемые при упаковке
├── crds/
│   └── openr.ag_openrags.yaml    # CRD OpenRAG (устанавливается автоматически)
└── templates/
    ├── _helpers.tpl               # Шаблонные помощники
    ├── NOTES.txt                  # Заметки после установки
    ├── deployment.yaml            # Развёртывание оператора
    ├── serviceaccount.yaml        # Сервисный аккаунт
    ├── role.yaml                  # ClusterRole для оператора
    ├── rolebinding.yaml           # ClusterRoleBinding
    ├── leader_election_role.yaml  # Роль для выборов лидера
    └── leader_election_rolebinding.yaml
```

### Конфигурация Helm-чарта

Ключевые настраиваемые значения в `values.yaml`:

```yaml
image:
  repository: ghcr.io/langflow-ai/openrag-operator
  tag: ""  # по умолчанию равно appVersion чарта
  pullPolicy: IfNotPresent

replicaCount: 1

resources:
  limits:
    cpu: 500m
    memory: 128Mi
  requests:
    cpu: 10m
    memory: 64Mi

leaderElection:
  enabled: true

nodeSelector: {}
tolerations: []
affinity: {}
```

### Операции с Helm-чартом

**Тест чарта:**
```bash
helm lint ./kubernetes/helm/operator
```

**Шаблонизация чарта (dry-run):**
```bash
helm template openrag-operator ./kubernetes/helm/operator \
  --namespace openrag-control
```

**Упаковка чарта:**
```bash
helm package ./kubernetes/helm/operator
```

**Обновление оператора:**
```bash
helm upgrade openrag-operator ./kubernetes/helm/operator \
  --namespace openrag-control
```

**Удаление:**
```bash
helm uninstall openrag-operator --namespace openrag-control
```

**Примечание:** CRD не обновляются автоматически Helm. Если CRD изменился, примените его вручную:
```bash
kubectl apply -f kubernetes/helm/operator/crds/openr.ag_openrags.yaml
```

## Обзор CR

```yaml
apiVersion: openr.ag/v1alpha1
kind: OpenRAG
metadata:
  name: my-openrag
spec:
  frontend:
    image: langflowai/openrag-frontend:latest
  backend:
    image: langflowai/openrag-backend:latest
    envSecret: my-backend-env      # Secret с ключом ".env"
    storage:
      enabled: true
      size: 10Gi
  langflow:
    image: langflowai/openrag-langflow:latest
    envSecret: my-langflow-env
    storage:
      enabled: true
      size: 10Gi
  opensearch:
    host: opensearch-coordinating.opensearch.svc.cluster.local
    credentialsSecret: opensearch-credentials   # ключи: username, password
  # docling:                        # необязательно
  #   host: docling-serve.docling.svc.cluster.local
  networkPolicy:
    enabled: false
```

Полный пример с аннотациями см. в [`config/samples/openrag_v1alpha1_openrag.yaml`](config/samples/openrag_v1alpha1_openrag.yaml).

## Процесс выпуска

Оператор использует GitHub Actions для автоматических выпусков:

### Публикация Docker-образа

Образы автоматически публикуются в GitHub Container Registry (GHCR) при отправке тега:

```bash
# Создайте и отправьте тег выпуска
git tag operator/v0.1.0
git push origin operator/v0.1.0
```

Это запускает рабочий процесс `.github/workflows/operator-release.yml`, который:
1. Собирает мультиархитектурные образы (linux/amd64, linux/arm64)
2. Отправляет их в `ghcr.io/<owner>/openrag-operator:v0.1.0`
3. Создаёт мультиархитектурный манифест с тегом `:latest`
4. Создаёт выпуск GitHub с заметками о выпуске

**Ручной запуск:**
Вы также можете запустить рабочий процесс выпуска вручную из интерфейса GitHub Actions с пользовательским тегом.

**Расположение образа:**
- Реестр: `ghcr.io`
- Репозиторий: `ghcr.io/langflow-ai/openrag-operator`
- Теги: `v0.1.0`, `v0.1.0-amd64`, `v0.1.0-arm64`, `latest`

### Публикация Helm-чарта

(Будет реализовано) Helm-чарты можно публиковать на GitHub Pages или в Helm-репозиторий с помощью GitHub Actions.
