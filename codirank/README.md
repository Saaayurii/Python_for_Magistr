# CoDiRank — Рекомендательная система мобильных приложений

Telegram-бот, подбирающий мобильные приложения через диалог. Использует локальную LLM (Qwen 2.5), PostgreSQL + pgvector и алгоритм CoDiRank.

## Требования

- Docker + Docker Compose
- Python 3.11+ (для запуска скриптов вне контейнера)
- ~6 ГБ свободного места (модель Qwen ~4.7 ГБ)
- Telegram Bot Token (от @BotFather)

---

## Быстрый старт

### 1. Клонировать и настроить переменные окружения

```bash
cd codirank
cp .env.example .env
```

Отредактировать `.env` — вписать `BOT_TOKEN`:

```bash
BOT_TOKEN=1234567890:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. Запустить инфраструктуру

```bash
docker compose up postgres ollama -d
```

> Порт PostgreSQL: **5434** (5432 и 5433 могут быть заняты другими сервисами).
> Порт Ollama: **11434**.

### 3. Загрузить модель Qwen

```bash
docker exec codirank-ollama-1 ollama pull qwen2.5:7b-instruct-q4_K_M
```

Размер: ~4.7 ГБ. Прогресс виден в терминале.

---

## Миграции базы данных

### Автоматическое создание таблиц (рекомендуется)

При старте бота таблицы создаются автоматически через `Base.metadata.create_all`.

### Через Alembic (опционально)

Установить зависимости:

```bash
pip install alembic asyncpg sqlalchemy pgvector
```

Применить первую миграцию:

```bash
alembic upgrade head
```

Создать новую миграцию после изменения моделей:

```bash
alembic revision --autogenerate -m "описание изменения"
alembic upgrade head
```

Откатить последнюю миграцию:

```bash
alembic downgrade -1
```

---

## Сидирование каталога приложений (загрузка данных)

### Шаг 1 — Загрузить приложения в базу данных

**Только iOS (iTunes API, ~3500 приложений, без файлов):**

```bash
python3 scripts/load_catalog.py
```

**Android + iOS (нужен файл `googleplaystore.csv` с Kaggle):**

Скачать датасет: https://www.kaggle.com/datasets/lava18/google-play-store-apps

```bash
python3 scripts/load_catalog.py /path/to/googleplaystore.csv
```

### Шаг 2 — Вычислить эмбеддинги для всех приложений

> Требует запущенного Ollama с моделью Qwen.

```bash
python3 scripts/embed_catalog.py
```

**Время работы:**
- CPU: ~2 часа на 3500 приложений (батч 32, ~75 сек/батч)
- GPU (NVIDIA): ~15-20 минут

Для GPU — раскомментировать секцию `deploy` в `docker-compose.yml`:

```yaml
ollama:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Шаг 3 — Создать HNSW-индекс (после заполнения эмбеддингов)

```bash
docker exec codirank-postgres-1 psql -U user -d codirank -c "
CREATE INDEX IF NOT EXISTS apps_embedding_hnsw
ON apps USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
"
```

---

## Запуск бота

### Через Docker Compose (продакшн)

```bash
docker compose up bot -d
```

### Локально (для разработки)

```bash
cd codirank
pip install -r bot/requirements.txt
export BOT_TOKEN=your_token
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5434/codirank
export OLLAMA_URL=http://localhost:11434
python3 bot/main.py
```

---

## Тесты

```bash
pip install pytest pytest-asyncio
python3 -m pytest tests/ -v
```

---

## Структура проекта

```
codirank/
├── bot/              — Telegram-бот (aiogram 3), FSM, хэндлеры
├── core/
│   ├── codirank/     — Алгоритм CoDiRank (профиль, ранкер, парсер атрибутов)
│   ├── llm/          — Клиент Ollama (embeddings, chat)
│   └── catalog/      — Загрузка каталога (Google Play CSV, iTunes API)
├── db/               — SQLAlchemy модели, репозитории, Alembic миграции
├── scripts/          — Одноразовые скрипты (сидирование, эмбеддинги, тесты)
└── tests/            — Unit-тесты алгоритма
```

## Алгоритм CoDiRank

Оценка приложения: `R(i,D,t) = β₁·cos(E(app), P(t)) + β₂·attr_match - β₃·reject_penalty`

Профиль пользователя обновляется на каждом ходу диалога:
`P(t) = α·P(t-1) + (1-α)·embed(сообщение)·вес`

Все коэффициенты настраиваются в `.env`.
