# Настройка версионирования Docusaurus

Версионирование документации в настоящее время **ОТКЛЮЧЕНО**, но настроено и готово к включению.
Конфигурация находится в `docusaurus.config.js`, в разделах, закомментированных.

Чтобы включить версионирование, выполните следующее:

1. Откройте `docusaurus.config.js`
2. Найдите раздел конфигурации версионирования (около строки 57)
3. Раскомментируйте конфигурацию версионирования:

```javascript
docs: {
  // ... other config
  lastVersion: 'current', // Use 'current' to make ./docs the latest version
  versions: {
    current: {
      label: 'Next (unreleased)',
      path: 'next',
    },
  },
  onlyIncludeVersions: ['current'], // Limit versions for faster builds
},
```

## Создание версий документации

Подробнее см. в [документации Docusaurus](https://docusaurus.io/docs/versioning).

1. Используйте команду CLI Docusaurus для создания версии.
```bash
# Create version 1.0.0 from current docs
npm run docusaurus docs:version 1.0.0
```

Эта команда:
- Скопирует всё содержимое каталога `docs/` в `versioned_docs/version-1.0.0/`
- Создаст файл боковой панели с версиями в `versioned_sidebars/version-1.0.0-sidebars.json`
- Добавит новую версию в `versions.json`

2. После создания версии обновите конфигурацию Docusaurus, чтобы включить несколько версий.
`lastVersion:'1.0.0'` делает релиз '1.0.0' версией `latest`.
`current` — это набор документов в процессе разработки, доступный по адресу `/docs/next`.
Чтобы удалить версию, удалите её из `onlyIncludeVersions`.

```javascript
docs: {
  // ... other config
  lastVersion: '1.0.0', // Make 1.0.0 the latest version
  versions: {
    current: {
      label: 'Next (unreleased)',
      path: 'next',
    },
    '1.0.0': {
      label: '1.0.0',
      path: '1.0.0',
    },
  },
  onlyIncludeVersions: ['current', '1.0.0'], // Include both versions
},
```

3. Проверьте развёртывание локально.

```bash
npm run build
npm run serve
```

4. Чтобы добавить последующие версии, повторите процесс: сначала выполните команду CLI, затем обновите `docusaurus.config.js`.

```bash
# Create version 2.0.0 from current docs
npm run docusaurus docs:version 2.0.0
```

После создания новой версии обновите `docusaurus.config.js`.

```javascript
docs: {
  lastVersion: '2.0.0', // Make 2.0.0 the latest version
  versions: {
    current: {
      label: 'Next (unreleased)',
      path: 'next',
    },
    '2.0.0': {
      label: '2.0.0',
      path: '2.0.0',
    },
    '1.0.0': {
      label: '1.0.0',
      path: '1.0.0',
    },
  },
  onlyIncludeVersions: ['current', '2.0.0', '1.0.0'], // Include all versions
},
```

## Отключение версионирования

1. Удалите конфигурацию `versions` из `docusaurus.config.js`.
2. Удалите каталоги `docs/versioned_docs/` и `docs/versioned_sidebars/`.
3. Удалите `docs/versions.json`.

## Ссылки

- [Официальная документация по версионированию Docusaurus](https://docusaurus.io/docs/versioning)
- [Рекомендации по версионированию Docusaurus](https://docusaurus.io/docs/versioning#recommended-practices)
