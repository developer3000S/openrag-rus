docker compose up -d
docker compose ps

echo "Файлы Docker Compose для OpenRAG развертывают следующие контейнеры:"

echo "Название контейнера	Адрес по умолчанию	Цель"
echo "OpenRAG Backend	http://localhost:8000	Сервер FastAPI и основные функциональные возможности."
echo "OpenRAG Frontend	http://localhost:3000	Веб-интерфейс React для взаимодействия с пользователем."
echo "LangFlow	http://localhost:7860	Механизм управления рабочими процессами на основе ИИ."
echo "OpenSearch	http://localhost:9200	Хранилище данных для знаний."
echo "OpenSearch Dashbord	http://localhost:5601	Интерфейс администрирования базы данных OpenSearch."

echo "Когда контейнеры запущены, вы можете получить доступ к своим сервисам OpenRAG по их адресам."
