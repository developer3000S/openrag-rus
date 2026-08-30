# Веб-сайт

Этот сайт создан с помощью [Docusaurus](https://docusaurus.io/), современного генератора статических сайтов.

## Установка

```bash
npm install
```

## Локальная разработка

```bash
npm start
```

Эта команда запускает локальный сервер разработки и открывает окно браузера. Большинство изменений отражаются в реальном времени без необходимости перезапуска сервера.

## Сборка

```bash
npm run build
```

Эта команда генерирует статический контент в каталог `build`, который можно разместить на любом сервисе хостинга статических файлов.

## Развёртывание

С использованием SSH:

```bash
USE_SSH=true npm run deploy
```

Без использования SSH:

```bash
GIT_USER=<Ваше имя пользователя GitHub> npm run deploy
```

Если вы используете GitHub Pages для хостинга, эта команда является удобным способом собрать сайт и опубликовать изменения в ветке `gh-pages`.

## Обновление PDF-документации OpenRAG

PDF-документация в `openrag/openrag-documents/openrag-documentation.pdf` используется приложением OpenRAG, поэтому держите её в актуальном состоянии.

Чтобы обновить PDF, выполните следующее:

1. Удалите элементы из файлов `docs/*.mdx`.
Контент внутри элементов tabs, details и summary скрыт в PDF-сборках, и его необходимо включить.
Чтобы удалить эти элементы, дайте вашей IDE приведённую ниже подсказку или нечто подобное.

   ```
   Flatten documentation for PDF: remove tabs and details elements
   In all MDX files in docs/docs/, flatten interactive elements:
   Remove all <Tabs> and <TabItem> components:
   Convert each tab's content to a regular section with an appropriate heading (### for subsections, ## for main sections)
   Show all tab content sequentially
   Remove the import statements for Tabs and TabItem where they're no longer used
   Remove all <details> and <summary> elements:
   Convert details content to regular text with an appropriate heading (### for subsections)
   Show all content directly (no collapsible sections)
   Keep all content visible — nothing should be hidden or collapsed
   Maintain proper formatting and structure
   Apply this to all documentation files that contain tabs or details elements so the content is fully flat and visible for PDF generation.
   ```

2. Проверьте свои файлы `.mdx`, чтобы убедиться, что эти элементы удалены.
Не коммитьте изменения.

3. Из каталога `openrag/docs` выполните следующую команду, чтобы собрать сайт с изменениями и создать PDF в `openrag/openrag-documents`.

   ```
   npm run build:pdf
   ```

4. Проверьте содержимое PDF, затем закоммитьте и создайте pull request.
