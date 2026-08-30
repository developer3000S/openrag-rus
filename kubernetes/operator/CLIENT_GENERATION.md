# Создание типизированного клиента Kubernetes для OpenRAG

В этом документе объясняется, как генерировать и использовать типизированные клиенты Kubernetes для CRD OpenRAG.

## Обзор

Вместо использования `unstructured.Unstructured` теперь можно использовать строго типизированные Go-клиенты, которые предоставляют:
- **Типобезопасность на этапе компиляции** - Обнаруживайте ошибки во время разработки, а не в рантайме
- **Автодополнение в IDE** - Лучше опыт разработчика
- **Более чистый код** - Без ручного перебора путей полей и утверждений типов

## Генерация Clientset

### Предварительные требования

```bash
# Установка зависимости code-generator
go get k8s.io/code-generator@v0.33.0
```

### Генерация клиентов

```bash
# Генерация clientset, listers и informers
make generate-client
```

Это создаст следующие пакеты:
- `pkg/generated/clientset/versioned` - Типизированный clientset
- `pkg/generated/listers/api/v1alpha1` - Listers для эффективного чтения
- `pkg/generated/informers/externalversions` - Informers для наблюдения за ресурсами

## Примеры использования

### До (использование Unstructured)

```go
import (
    "k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
    "k8s.io/apimachinery/pkg/runtime/schema"
)

// Create unstructured client
dynamicClient, err := dynamic.NewForConfig(config)
gvr := schema.GroupVersionResource{
    Group:    "openr.ag",
    Version:  "v1alpha1",
    Resource: "openrags",
}

// Get OpenRAG (weakly typed - runtime errors)
obj, err := dynamicClient.Resource(gvr).Namespace("default").Get(ctx, "my-openrag", metav1.GetOptions{})
if err != nil {
    return err
}

// Manual field navigation (error-prone)
spec, found, err := unstructured.NestedMap(obj.Object, "spec")
backend, found, err := unstructured.NestedMap(spec, "backend")
image, found, err := unstructured.NestedString(backend, "image")
// No compile-time type checking!
```

### После (использование типизированного клиента)

```go
import (
    openragv1alpha1 "github.com/langflow-ai/openrag-operator/api/v1alpha1"
    clientset "github.com/langflow-ai/openrag-operator/pkg/generated/clientset/versioned"
)

// Create typed client
client, err := clientset.NewForConfig(config)

// Get OpenRAG (strongly typed - compile-time safety!)
openrag, err := client.OpenrV1alpha1().OpenRAGs("default").Get(ctx, "my-openrag", metav1.GetOptions{})
if err != nil {
    return err
}

// Direct field access with type safety
image := openrag.Spec.Backend.Image  // ✅ Type-safe!
replicas := openrag.Spec.Backend.Replicas  // ✅ Auto-complete!
```

## Полный пример: создание экземпляра OpenRAG

```go
package main

import (
    "context"
    "fmt"

    corev1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/api/resource"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/client-go/tools/clientcmd"
    "k8s.io/utils/ptr"

    openragv1alpha1 "github.com/langflow-ai/openrag-operator/api/v1alpha1"
    clientset "github.com/langflow-ai/openrag-operator/pkg/generated/clientset/versioned"
)

func main() {
    // Load kubeconfig
    config, err := clientcmd.BuildConfigFromFlags("", "/path/to/kubeconfig")
    if err != nil {
        panic(err)
    }

    // Create OpenRAG typed client
    client, err := clientset.NewForConfig(config)
    if err != nil {
        panic(err)
    }

    // Define OpenRAG instance
    openrag := &openragv1alpha1.OpenRAG{
        ObjectMeta: metav1.ObjectMeta{
            Name:      "my-openrag",
            Namespace: "default",
        },
        Spec: openragv1alpha1.OpenRAGSpec{
            TenantID: "tenant-123",
            Frontend: openragv1alpha1.FrontendSpec{
                ComponentSpec: openragv1alpha1.ComponentSpec{
                    Image:    "myregistry/openrag-frontend:v1.0.0",
                    Replicas: ptr.To(int32(2)),
                    Resources: corev1.ResourceRequirements{
                        Requests: corev1.ResourceList{
                            corev1.ResourceCPU:    resource.MustParse("100m"),
                            corev1.ResourceMemory: resource.MustParse("256Mi"),
                        },
                    },
                },
            },
            Backend: openragv1alpha1.BackendSpec{
                ComponentSpec: openragv1alpha1.ComponentSpec{
                    Image:    "myregistry/openrag-backend:v1.0.0",
                    Replicas: ptr.To(int32(3)),
                    Env: []corev1.EnvVar{
                        {Name: "CUSTOM_VAR", Value: "custom_value"},
                    },
                },
                Storage: &openragv1alpha1.PersistenceSpec{
                    Enabled: true,
                    Size:    resource.MustParse("10Gi"),
                },
            },
            Langflow: openragv1alpha1.LangflowSpec{
                ComponentSpec: openragv1alpha1.ComponentSpec{
                    Image:    "myregistry/langflow:v1.0.0",
                    Replicas: ptr.To(int32(2)),
                },
                PVCReclaimPolicy: openragv1alpha1.PVCReclaimRetain,
            },
        },
    }

    // Create the resource
    result, err := client.OpenrV1alpha1().OpenRAGs("default").Create(
        context.Background(),
        openrag,
        metav1.CreateOptions{},
    )
    if err != nil {
        panic(err)
    }

    fmt.Printf("Created OpenRAG: %s\n", result.Name)

    // Update the resource
    result.Spec.Backend.Replicas = ptr.To(int32(5))
    updated, err := client.OpenrV1alpha1().OpenRAGs("default").Update(
        context.Background(),
        result,
        metav1.UpdateOptions{},
    )
    if err != nil {
        panic(err)
    }

    fmt.Printf("Updated OpenRAG backend replicas to: %d\n", *updated.Spec.Backend.Replicas)

    // List all OpenRAG instances
    list, err := client.OpenrV1alpha1().OpenRAGs("").List(
        context.Background(),
        metav1.ListOptions{},
    )
    if err != nil {
        panic(err)
    }

    fmt.Printf("Found %d OpenRAG instances\n", len(list.Items))
    for _, item := range list.Items {
        fmt.Printf("  - %s/%s (Phase: %s)\n", item.Namespace, item.Name, item.Status.Phase)
    }
}
```

## Использование Informers (эффективное наблюдение)

Informers предоставляют эффективное кэширование и наблюдение за ресурсами:

```go
import (
    "time"

    "k8s.io/client-go/tools/cache"

    informers "github.com/langflow-ai/openrag-operator/pkg/generated/informers/externalversions"
)

// Create informer factory
informerFactory := informers.NewSharedInformerFactory(client, time.Minute*10)

// Get OpenRAG informer
openragInformer := informerFactory.Openr().V1alpha1().OpenRAGs()

// Add event handlers
openragInformer.Informer().AddEventHandler(cache.ResourceEventHandlerFuncs{
    AddFunc: func(obj interface{}) {
        openrag := obj.(*openragv1alpha1.OpenRAG)
        fmt.Printf("OpenRAG added: %s/%s\n", openrag.Namespace, openrag.Name)
    },
    UpdateFunc: func(old, new interface{}) {
        newOpenRAG := new.(*openragv1alpha1.OpenRAG)
        fmt.Printf("OpenRAG updated: %s/%s\n", newOpenRAG.Namespace, newOpenRAG.Name)
    },
    DeleteFunc: func(obj interface{}) {
        openrag := obj.(*openragv1alpha1.OpenRAG)
        fmt.Printf("OpenRAG deleted: %s/%s\n", openrag.Namespace, openrag.Name)
    },
})

// Start informers
stopCh := make(chan struct{})
defer close(stopCh)
informerFactory.Start(stopCh)

// Wait for cache sync
if !cache.WaitForCacheSync(stopCh, openragInformer.Informer().HasSynced) {
    panic("Failed to sync cache")
}

// Now use the lister for efficient reads
lister := openragInformer.Lister()
openrags, err := lister.OpenRAGs("default").List(labels.Everything())
```

## Преимущества

### Типобезопасность
```go
// ❌ Unstructured - Runtime error
image := obj.Object["spec"].(map[string]interface{})["backend"].(map[string]interface{})["image"].(string)

// ✅ Typed - Compile-time error if field doesn't exist
image := openrag.Spec.Backend.Image
```

### Поддержка IDE
- Автодополнение для всех полей
- Переход к определению
- Встроенная документация
- Поддержка рефакторинга

### Более чистый код
- Без утверждений типов
- Без ручного перебора путей полей
- Легче читать и поддерживать

## Повторная генерация клиентов

Запускайте эту команду всякий раз при изменении типов CRD:

```bash
make generate        # Перегенерировать методы DeepCopy
make generate-client # Перегенерировать clientsets, listers, informers
```

## Распространение

### Вариант 1: публикация как Go-модуль (рекомендуется)

Пользователи могут импортировать напрямую:

```go
import clientset "github.com/langflow-ai/openrag-operator/pkg/generated/clientset/versioned"
```

### Вариант 2: копирование сгенерированного кода

Если пользователи не хотят зависеть от всего вашего модуля, они могут скопировать сгенерированный код в свой проект:

```bash
cp -r pkg/generated /path/to/their/project/
```

## Устранение неполадок

### `code-generator` не найден

Если вы видите эту ошибку:
```
Error: k8s.io/code-generator not found in module cache
```

Выполните:
```bash
go mod download k8s.io/code-generator
# ИЛИ
go get k8s.io/code-generator@v0.33.0
go mod tidy
```

Зависимость уже есть в `go.mod`, поэтому `go mod download` должно быть достаточно.

### Отказ в доступе при запуске скрипта

```bash
chmod +x hack/update-codegen.sh
```

### Сгенерированный код не в системе контроля версий

Рекомендуется коммитить сгенерированный код в систему контроля версий, чтобы пользователи могли использовать его без запуска генерации кода.

### Сбои проверки CI

Если ваш pull request завершается ошибкой с:

```text
Error: git diff --exit-code pkg/generated/
```

Это означает, что вы изменили типы API, но не перегенерировали типизированный клиент. Исправьте это:

```bash
make generate-client
git add pkg/generated/
git commit --amend --no-edit
git push --force-with-lease
```

Наш CI автоматически проверяет, что сгенерированный код актуален, чтобы предотвратить несогласованности.

## Внесение вклада

При изменении типов API в `api/v1alpha1/` всегда запускайте:

```bash
make generate        # Перегенерировать код deepcopy
make manifests       # Перегенерировать CRD и RBAC
make generate-client # Перегенерировать типизированный клиент
git add api/ config/ pkg/generated/
git commit -m "feat: add new field to OpenRAG spec"
```

Подробности см. в [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Ссылки

- [Kubernetes Code Generator](https://github.com/kubernetes/code-generator)
- [Sample Controller](https://github.com/kubernetes/sample-controller)
- [Документация Client-go](https://github.com/kubernetes/client-go)
