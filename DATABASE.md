# DATABASE

Схема базы данных SQLite для ChatList.

## Таблица `prompts`
Хранит промты пользователя.

Поля:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `created_at` TEXT NOT NULL
- `prompt` TEXT NOT NULL
- `tags` TEXT

## Таблица `models`
Хранит параметры подключаемых нейросетей. API-ключи не хранятся в БД, вместо них хранится имя переменной из `.env`.

Поля:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `name` TEXT NOT NULL
- `api_url` TEXT NOT NULL
- `api_key_env` TEXT NOT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1

## Таблица `results`
Хранит сохраненные пользователем результаты.

Поля:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `prompt_id` INTEGER NOT NULL
- `model_id` INTEGER NOT NULL
- `response_text` TEXT NOT NULL
- `created_at` TEXT NOT NULL

Связи:
- `prompt_id` -> `prompts.id`
- `model_id` -> `models.id`

## Таблица `settings`
Хранит настройки приложения.

Поля:
- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `key` TEXT NOT NULL UNIQUE
- `value` TEXT

## Пример SQL-схемы

```sql
CREATE TABLE prompts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  prompt TEXT NOT NULL,
  tags TEXT
);

CREATE TABLE models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  api_url TEXT NOT NULL,
  api_key_env TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prompt_id INTEGER NOT NULL,
  model_id INTEGER NOT NULL,
  response_text TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (prompt_id) REFERENCES prompts(id),
  FOREIGN KEY (model_id) REFERENCES models(id)
);

CREATE TABLE settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT NOT NULL UNIQUE,
  value TEXT
);
```
