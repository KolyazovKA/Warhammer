# Warhammer RAG Chatbot

Чат-бот для анализа документов на основе RAG (Retrieval-Augmented Generation). Пользователь загружает файлы (PDF, DOCX, EPUB, FB2), система разбивает их на смысловые фрагменты, сохраняет в векторную базу данных ChromaDB и отвечает на вопросы, опираясь исключительно на загруженные материалы. В качестве языковой модели используется DeepSeek.

---

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Запуск в режиме разработки](#запуск-в-режиме-разработки)
- [Запуск через Docker](#запуск-через-docker)
- [Переменные окружения](#переменные-окружения)
- [Архитектура системы](#архитектура-системы)
- [Backend: подробное описание](#backend-подробное-описание)
  - [Точка входа и жизненный цикл приложения](#точка-входа-и-жизненный-цикл-приложения)
  - [Конфигурация](#конфигурация)
  - [API: загрузка документов](#api-загрузка-документов)
  - [Парсеры документов](#парсеры-документов)
  - [Разбивка текста на чанки](#разбивка-текста-на-чанки)
  - [Векторная база данных ChromaDB](#векторная-база-данных-chromadb)
  - [Эмбеддинги](#эмбеддинги)
  - [API: семантический поиск и ответ](#api-семантический-поиск-и-ответ)
  - [API: список документов](#api-список-документов)
- [Frontend](#frontend)
- [Структура проекта](#структура-проекта)

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd Warhammer

# 2. Создать .env файл
cp .env.example .env
# Открыть .env и вставить ваш DEEPSEEK_API_KEY

# 3. Запустить через Docker
docker-compose -f docker/docker-compose.yaml up --build
```

После запуска:
- Фронтенд: http://localhost:8080
- Backend API / Swagger: http://localhost:8081/docs

---

## Запуск в режиме разработки

### Требования

- Python 3.11+
- Node.js 20+
- DeepSeek API ключ

### Backend

```bash
# Установить зависимости
pip install -r requirements.txt

# Создать .env (если ещё не создан)
cp .env.example .env
# Отредактировать .env, вставить DEEPSEEK_API_KEY

# Запустить (из src/backend — пути __file__-относительные)
cd src/backend
python main.py
```

Сервер запустится на `http://localhost:8081`. Swagger UI доступен по адресу `http://localhost:8081/docs`.

### Frontend

```bash
cd src/frontend/frontend-proto
npm install
npm run dev
```

Фронтенд запустится на `http://localhost:8082`.

### Производственная сборка фронтенда

```bash
cd src/frontend/frontend-proto
npm run build
# Статические файлы появятся в dist/
```

---

## Запуск через Docker

Сборка и запуск всего стека (из корня репозитория):

```bash
docker-compose -f docker/docker-compose.yaml up --build
```

Запуск только одного сервиса:

```bash
# Только backend
docker-compose -f docker/docker-compose.yaml up --build wh-backend

# Только frontend
docker-compose -f docker/docker-compose.yaml up --build wh-frontend
```

Данные ChromaDB и загруженные файлы хранятся в именованных Docker volumes (`choma_db_data`, `files_data`) — они **переживают пересборку образов** и удаление контейнеров.

Docker образы используют многоступенчатую сборку:
- **Backend**: Python 3.11-slim. Зависимости устанавливаются на первом этапе в изолированный venv, на второй этап копируется только виртуальное окружение. Приложение запускается от непривилегированного пользователя `appuser`.
- **Frontend**: Node 20-alpine для сборки React-приложения, затем Nginx 1.27-alpine для раздачи статики.

---

## Переменные окружения

Создайте файл `.env` в корне репозитория (шаблон — `.env.example`):

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | Да | — | API ключ DeepSeek |
| `EMBEDDING_BACKEND` | Нет | `deepseek` | Движок эмбеддингов: `deepseek` или `gte-small` |
| `DEEPSEEK_TEMPERATURE` | Нет | `0.8` | Температура генерации (0.0–2.0) |
| `BASE_URL` | Нет | `http://localhost:8081` | Публичный адрес backend (используется в ссылках на файлы) |

`gte-small` — локальная модель эмбеддингов, не требует API и не тратит кредиты. Требует `pip install sentence-transformers`. Подходит для офлайн-использования и разработки.

---

## Архитектура системы

```
┌─────────────────────────────────┐
│   React Frontend  :8080 / :8082 │
└──────────────┬──────────────────┘
               │ HTTP REST
               ▼
┌─────────────────────────────────┐
│     FastAPI Backend  :8081      │
│                                 │
│  POST /api/documents/upload     │
│    → валидация (magic bytes)    │
│    → парсер по расширению       │
│    → smart_chunking()           │
│    → ChromaDB.upsert()          │
│    → сохранение файла на диск   │
│                                 │
│  POST /api/chat/semantics       │
│    → ChromaDB.query(n=15)       │
│    → сборка промпта с чанками   │
│    → DeepSeek API               │
│    → ответ + источники          │
│                                 │
│  GET /get_books                 │
│    → список файлов из ./files/  │
│                                 │
│  GET /files/{name}              │
│    → StaticFiles (оригиналы)    │
└──────────────┬──────────────────┘
               │
       ┌───────┴────────┐
       │                │
  ┌────▼─────┐    ┌─────▼──────┐
  │ ChromaDB │    │  ./files/  │
  │ choma_db/│    │ (originals)│
  └──────────┘    └────────────┘
```

**Поток загрузки документа:**
1. Файл проходит валидацию: проверяется размер, расширение и magic-байты в заголовке.
2. Текст извлекается парсером, соответствующим формату файла.
3. Текст разбивается на перекрывающиеся чанки с учётом границ предложений.
4. Чанки и их метаданные сохраняются в ChromaDB через `upsert` — повторная загрузка обновляет, а не дублирует данные.
5. Оригинальный файл сохраняется на диск для раздачи через `/files/`.

**Поток ответа на вопрос:**
1. Вопрос пользователя превращается в вектор той же эмбеддинг-моделью, что использовалась при индексации.
2. ChromaDB находит 15 наиболее близких чанков по косинусному расстоянию.
3. Из чанков и их метаданных собирается промпт.
4. DeepSeek генерирует ответ строго на основе переданного контекста.
5. Клиенту возвращается ответ и список чанков-источников.

---

## Backend: подробное описание

### Точка входа и жизненный цикл приложения

**Файл:** `src/backend/main.py`

FastAPI приложение использует механизм `lifespan` — функцию-генератор, которая выполняется при старте и остановке сервера. Это предпочтительнее устаревших `@app.on_event("startup")` / `@app.on_event("shutdown")` хуков, так как оба этапа описаны в одном месте и ресурсы гарантированно освобождаются при выходе из `async with`.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Config.validate()        # проверяем API ключ до старта
    Chroma.initialize()      # подключаем/создаём ChromaDB коллекцию
    _FILES_DIR.mkdir(...)    # создаём папку для файлов
    async with httpx.AsyncClient(timeout=60.0) as client:
        app.state.http_client = client   # единый HTTP клиент на всё приложение
        yield
    # при выходе из `async with` клиент закрывается автоматически
```

**Почему единый `httpx.AsyncClient`?** Создание нового HTTP-клиента на каждый запрос означает создание нового connection pool. Единый клиент переиспользует TCP-соединения к DeepSeek API, что снижает латентность и нагрузку на сеть. Клиент хранится в `app.state`, откуда его забирают обработчики через объект `Request`.

CORS настроен разрешающим только `localhost:8080` и `localhost:8082`. В продакшне следует заменить на реальный домен фронтенда.

---

### Конфигурация

**Файл:** `src/backend/config.py`

Все параметры приложения собраны в одном классе `Config`. Значения читаются из переменных окружения при старте; если переменная не задана, используется значение по умолчанию.

```python
class Config:
    DEEPSEEK_API_KEY: str   = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_TEMPERATURE    = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.8"))
    BASE_URL: str           = os.getenv("BASE_URL", "http://localhost:8081")
    EMBEDDING_BACKEND       = os.getenv("EMBEDDING_BACKEND", "deepseek")
```

Метод `Config.validate()` вызывается в `lifespan` до того, как приложение начнёт принимать запросы. Если API ключ не задан — сервер не стартует с понятной ошибкой, а не падает в рантайме при первом запросе.

`BASE_URL` используется при формировании ссылок на скачивание файлов. В Docker-окружении или при размещении за reverse proxy нужно установить эту переменную в реальный публичный адрес сервера.

---

### API: загрузка документов

**Файл:** `src/backend/api/documents/upload.py`  
**Endpoint:** `POST /api/documents/upload`

#### Валидация файла

Валидация происходит в два шага перед любой обработкой:

**1. Проверка `Content-Length` заголовка** (ранний выход):
```python
content_length = request.headers.get("content-length")
if content_length and int(content_length) > MAX_FILE_SIZE:
    raise HTTPException(400, "File too large (max 60 MB)")
```
Это позволяет отклонить слишком большой файл до полного чтения тела запроса в память.

**2. Валидация по magic-байтам** после чтения:
```python
_MAGIC = [
    (b'%PDF',           'pdf'),
    (b'PK\x03\x04',    'zip'),   # DOCX и EPUB — ZIP-архивы
    (b'\xd0\xcf\x11\xe0', 'ole'), # legacy .doc
    (b'<?xml',          'xml'),   # FB2
    (b'<Fict',          'xml'),   # FB2 без XML-декларации
]
```
Проверяется, что первые 8 байт файла соответствуют ожидаемому типу по расширению. Это защищает от переименованных файлов — нельзя загрузить `.exe`, назвав его `.pdf`.

#### Порядок операций и обработка ошибок

Операции выполняются строго в следующем порядке:

```
1. Валидация (400 — ранний выход, файл не читается полностью)
2. Парсинг текста из файла         → 422 при ошибке парсера
3. Разбивка на чанки               → 422 если текст пустой
4. Upsert в ChromaDB               → 500 при ошибке индексации
5. Сохранение оригинала на диск    → 500 при ошибке записи
```

Порядок 4 → 5 выбран намеренно: если `upsert` прошёл, но сохранение на диск упало, пользователь получает ошибку и может повторить загрузку. При повторе `upsert` обновит те же чанки (по стабильному ID), а файл будет записан. Обратный порядок был бы хуже: файл на диске без индекса обнаружить труднее.

Вместо `collection.add()` используется `collection.upsert()` — при повторной загрузке файла с тем же именем чанки обновляются, а не дублируются. `add()` выбрасывал бы ошибку на уже существующих ID.

#### Идентификаторы чанков

```python
def _chunk_id(filename: str, index: int) -> str:
    safe = hashlib.sha1(filename.encode()).hexdigest()[:16]
    return f"{safe}_chunk_{index}"
```

ID формируется как хэш имени файла + номер чанка. Это решает две проблемы: имя файла от пользователя не попадает напрямую в ChromaDB, и ID остаётся стабильным при повторных загрузках того же файла — что обеспечивает корректный upsert.

#### Выполнение в executor

ChromaDB вызывает функцию эмбеддингов синхронно. Если вызвать `collection.upsert()` напрямую из async-обработчика, он заблокирует event loop FastAPI на время HTTP-запроса к DeepSeek Embeddings API. Решение — выполнение в thread pool:

```python
loop = asyncio.get_event_loop()
await loop.run_in_executor(
    None,
    lambda: Chroma.collection.upsert(documents=documents, metadatas=metadatas, ids=ids),
)
```

---

### Парсеры документов

**Директория:** `src/backend/parsers/`

Каждый формат обрабатывается отдельным модулем. Все парсеры принимают `bytes` и возвращают `str` — это упрощает тестирование (не нужны файлы на диске) и позволяет работать с содержимым файла в памяти.

| Файл | Формат | Библиотека | Особенности |
|---|---|---|---|
| `simple_pdf.py` | PDF | PyPDF2 | Добавляет маркеры `PAGE N` в текст; они подхватываются `smart_chunking` для метаданных страниц |
| `docx_parser.py` | DOCX | python-docx | Обходит параграфы документа; таблицы и header/footer не извлекаются |
| `epub_new.py` | EPUB | ebooklib + BeautifulSoup | Парсит каждый HTML-документ внутри ZIP-архива; возвращает список глав с заголовками |
| `fb2.py` | FB2 | defusedxml | Использует `defusedxml` вместо стандартного `xml.etree.ElementTree` |

**Почему `defusedxml` для FB2?** Стандартный `xml.etree.ElementTree` уязвим к XML-бомбам (Billion Laughs) и XXE-атакам: специально сформированный файл может потребить гигабайты памяти или прочитать произвольные файлы с сервера через XML-сущности. `defusedxml` — drop-in замена, которая отключает опасные возможности XML по умолчанию.

**Почему PDF только с текстовым слоем?** Добавление OCR (Tesseract и т.п.) значительно усложняет зависимости и увеличивает время обработки. Для целевых материалов наличие текстового слоя является нормой.

---

### Разбивка текста на чанки

**Файл:** `src/backend/util.py`, функция `smart_chunking()`

RAG-система не может передать в LLM весь текст книги целиком — есть ограничение на длину контекста. Текст нужно разбить на фрагменты, из которых потом будут выбраны наиболее релевантные.

#### Алгоритм

```
1. Разбить текст по границам предложений (regex: .  !  ?)
2. Накапливать предложения, пока их суммарная длина < chunk_size (1000 символов)
3. При превышении → зафиксировать чанк, начать новый с перекрытием
4. Для каждого чанка извлечь метаданные: даты и номера страниц
```

#### Перекрытие (overlap)

```python
overlap_sentences = []
overlap_len = 0
for s in reversed(current_chunk):
    if overlap_len + len(s) > overlap:  # overlap = 200 символов
        break
    overlap_sentences.insert(0, s)
    overlap_len += len(s)
current_chunk = overlap_sentences
```

Берём предложения с конца предыдущего чанка, пока их суммарная длина не достигнет 200 символов. Это гарантирует, что каждый следующий чанк начинается с небольшого контекста из предыдущего — важно для вопросов, ответ на которые лежит на стыке двух фрагментов.

**Почему границы предложений, а не фиксированное количество символов?** Простая нарезка по N символов разрывает предложения посередине. Это ухудшает качество эмбеддинга (неполная мысль даёт менее точный вектор) и читаемость чанка для LLM.

#### Метаданные чанков

```python
{
    'text': '...',
    'metadata': {
        'chunk_type': 'natural_break',
        'dates': ['2024-01-15', '15/01/2024'],  # найденные в тексте даты
        'pages': [12, 13],                       # PAGE N маркеры из PDF
    }
}
```

Даты извлекаются regex-паттерном, покрывающим форматы `DD/MM/YYYY`, `YYYY-MM-DD` и `Month DD, YYYY`. Номера страниц — маркеры `PAGE N`, которые PDF-парсер вставляет в текст. Эти метаданные попадают в ответ API и позволяют пользователю понять, из какой части документа взята информация.

---

### Векторная база данных ChromaDB

**Файл:** `src/backend/persistence/chroma.py`

ChromaDB — встраиваемая векторная БД, не требующая отдельного сервиса. Она хранит текст чанков, их векторные представления и метаданные, и умеет искать ближайшие векторы по косинусному расстоянию.

```python
_DB_PATH = Path(__file__).parent.parent / "choma_db"

class Chroma:
    @staticmethod
    def initialize():
        Chroma.client = PersistentClient(path=str(_DB_PATH))
        Chroma.collection = Chroma.client.get_or_create_collection(
            name="choma_collection",
            embedding_function=embedding_func,
        )
```

**Почему абсолютный путь?** Относительный путь `"choma_db"` разрешается относительно текущей рабочей директории процесса. При запуске из разных директорий (`cd src/backend && python main.py` vs `python src/backend/main.py`) создавались бы разные базы. Абсолютный путь через `Path(__file__)` всегда указывает в одно место — рядом с модулем `chroma.py`.

**`get_or_create_collection`** — идемпотентная операция: при первом запуске создаёт коллекцию, при последующих переиспользует существующую. Функция эмбеддингов передаётся в коллекцию один раз, после чего ChromaDB автоматически применяет её при каждом `query()` и `upsert()`.

**Параметры коллекции:**
- Название: `choma_collection`
- Метаданные чанка: `source`, `chunk_num`, `chunk_type`, `dates`, `pages`

---

### Эмбеддинги

**Директория:** `src/backend/embeddings/`

Эмбеддинг — числовой вектор (обычно 1000–4000 чисел), кодирующий смысл текста. Семантически похожие тексты дают близкие векторы. Именно это позволяет ChromaDB находить релевантные чанки по смыслу вопроса, а не только по совпадению слов.

Критически важно использовать **одну и ту же модель** при индексации и при поиске. Функция эмбеддингов передаётся в ChromaDB-коллекцию, которая применяет её автоматически — это исключает рассинхрон.

Выбор движка задаётся в `embeddings/function.py`:
```python
if Config.EMBEDDING_BACKEND == "gte-small":
    embedding_func = GTESmallEmbeddingFunction()
else:
    embedding_func = DeepSeekEmbeddingFunction(api_key=Config.DEEPSEEK_API_KEY)
```

#### DeepSeek Embeddings (`embeddings/deepseek.py`)

```python
class DeepSeekEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __call__(self, texts):
        payload = {"input": texts, "model": "deepseek-embedding"}
        resp = requests.post(Config.DEEPSEEK_EMBED_URL, ...)
        return [item["embedding"] for item in resp.json()["data"]]
```

Используется по умолчанию (`EMBEDDING_BACKEND=deepseek`). Тексты отправляются батчем в DeepSeek API, возвращается список векторов. Требует интернет-соединения и тратит API-кредиты.

#### GTE-Small (`embeddings/gte_small.py`)

```python
class GTESmallEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __init__(self):
        self.model = SentenceTransformer("thenlper/gte-small")

    def __call__(self, texts):
        return self.model.encode(texts, normalize_embeddings=True).tolist()
```

Локальная модель (~130 МБ), работает без API. Активируется через `EMBEDDING_BACKEND=gte-small`. Требует `pip install sentence-transformers`. Качество несколько ниже, чем у DeepSeek, но подходит для офлайн-использования.

> **Важно:** нельзя переключить `EMBEDDING_BACKEND` для уже заполненной базы. Векторы, созданные одной моделью, несовместимы с другой. При смене модели нужно удалить директорию `choma_db/` и переиндексировать все документы.

---

### API: семантический поиск и ответ

**Файл:** `src/backend/api/chat/semantics.py`  
**Endpoint:** `POST /api/chat/semantics`

#### Запрос и ответ

```json
// Запрос
{ "question": "Какое оружие использует Space Marine?" }

// Ответ
{
  "answer": "Основное оружие Space Marine — болтер... [Источник: codex.pdf, стр. 42]",
  "sources": [
    {
      "text": "Болтер является стандартным оружием...",
      "metadata": { "source": "codex.pdf", "chunk_num": 5, "pages": [42] }
    }
  ]
}
```

#### Поиск по базе

```python
results = await loop.run_in_executor(
    None,
    lambda: Chroma.collection.query(query_texts=[query.question], n_results=15),
)
```

ChromaDB превращает вопрос в вектор той же функцией эмбеддингов и находит 15 ближайших чанков. Число 15 выбрано как баланс между полнотой контекста и длиной промпта. Запрос выполняется через `run_in_executor` по той же причине, что и `upsert` при загрузке — ChromaDB синхронна и блокировала бы event loop.

При пустой коллекции (документы ещё не загружены) ChromaDB возвращает пустой результат. Эта ситуация обрабатывается явно:

```python
if not docs or not docs[0]:
    return {"answer": "Не найдено в базе Chroma", "sources": []}
```

#### Сборка промпта

```python
prompt = (
    "Ты ассистент, отвечающий только на основе базы Chroma.\n"
    "Вот найденная информация с метаданными:\n"
    f"{context_text}\n\n"
    "---\n"
    f"Вопрос пользователя: {query.question}\n\n"
    "Если ответа нет — скажи 'Не найдено в базе Chroma'.\n"
    "Если отвечаешь, укажи источник и страницы."
)
```

Вопрос пользователя отделён от контекста явным разделителем `---`. Это снижает риск prompt injection: если в вопросе будут инструкции вроде «игнорируй всё выше», они попадут в секцию вопроса, а не в системные инструкции. Дополнительно введено ограничение длины вопроса — 2000 символов.

Каждый чанк в контексте снабжён метаданными:
```
[текст чанка]

Source: codex.pdf
Pages: 42, 43
Dates: 2023-01-15
```

Это позволяет LLM указать точный источник в ответе.

#### Вызов DeepSeek API

```python
http_client: httpx.AsyncClient = request.app.state.http_client
resp = await http_client.post(Config.DEEPSEEK_API_URL, headers=headers, json=payload)
```

Используется общий `AsyncClient` из `app.state` — соединение с DeepSeek переиспользуется между запросами. Таймаут 60 секунд задан при создании клиента в `lifespan`.

Ошибки явно разделены по типу:
- `HTTPStatusError` (4xx/5xx от DeepSeek) → 502 с кодом ошибки
- `RequestError` (сеть недоступна) → 502 с сообщением о недоступности
- Некорректная структура ответа (KeyError/IndexError) → 502, детали логируются, пользователю не раскрываются

---

### API: список документов

**Endpoint:** `GET /get_books`

Возвращает словарь `{имя_файла: ссылка_на_скачивание}` для всех файлов в директории `src/backend/files/`.

```python
files = {
    filename: f"{Config.BASE_URL}/files/{quote(filename)}"
    for filename in os.listdir(_FILES_DIR)
    if (_FILES_DIR / filename).is_file()
}
```

Ссылки формируются через `Config.BASE_URL` (настраивается через env), а имена кодируются через `urllib.parse.quote` для корректной обработки пробелов и кириллицы в URL.

Сами файлы раздаются через `StaticFiles` mount:

```python
app.mount("/files", StaticFiles(directory=str(_FILES_DIR)), name="files")
```

FastAPI / Starlette раздаёт файлы напрямую из файловой системы, поддерживая `Range` заголовки (частичная загрузка) и корректные `Content-Type`.

---

## Frontend

Single-page React приложение (`src/frontend/frontend-proto/src/App.tsx`). Весь UI реализован в одном компоненте.

**Основные возможности:**
- Чат-интерфейс с историей сообщений в текущей сессии
- Загрузка файлов через кнопку или drag & drop на любую область страницы
- Отображение статуса загрузки каждого файла (загрузка / успех / ошибка)
- Боковая панель «Источники» со списком загруженных документов и ссылками на скачивание
- Typing indicator во время ожидания ответа
- Таймаут запроса 60 секунд с сообщением пользователю

**Клиентские ограничения** (применяются только на фронтенде, не на бэкенде):
- Не более 5 вопросов в сессии
- Не более 5 файлов за сессию
- Суммарный размер файлов не более 60 МБ

**Производственный Nginx** (`docker/nginx.frontend.conf`) настроен на:
- SPA fallback: все неизвестные пути отдают `index.html`
- Долгосрочный кэш для хэшированных ассетов (JS, CSS с content-hash в имени от Vite)
- Запрет кэширования `index.html` — чтобы новые деплои применялись сразу
- Gzip-сжатие текстовых ресурсов

---

## Структура проекта

```
Warhammer/
├── .env.example                    # Шаблон переменных окружения
├── requirements.txt                # Python зависимости
├── docker/
│   ├── docker-compose.yaml
│   ├── WH.Backend.Dockerfile       # Многоступенчатая сборка Python
│   ├── WH.Frontend.Dockerfile      # Node сборка + Nginx раздача
│   └── nginx.frontend.conf         # Nginx конфиг для SPA
└── src/
    ├── backend/
    │   ├── main.py                 # FastAPI app, lifespan, роутинг
    │   ├── config.py               # Конфигурация из env
    │   ├── util.py                 # smart_chunking(), clean_text()
    │   ├── api/
    │   │   ├── chat/
    │   │   │   └── semantics.py    # POST /api/chat/semantics
    │   │   └── documents/
    │   │       └── upload.py       # POST /api/documents/upload
    │   ├── parsers/
    │   │   ├── simple_pdf.py       # PDF → str (PyPDF2)
    │   │   ├── docx_parser.py      # DOCX → str (python-docx)
    │   │   ├── epub_new.py         # EPUB → chapters dict (ebooklib)
    │   │   └── fb2.py              # FB2 → str (defusedxml)
    │   ├── embeddings/
    │   │   ├── function.py         # Выбор движка по EMBEDDING_BACKEND
    │   │   ├── deepseek.py         # DeepSeek Embeddings API
    │   │   └── gte_small.py        # Локальная модель thenlper/gte-small
    │   ├── persistence/
    │   │   └── chroma.py           # ChromaDB singleton
    │   ├── schemas/
    │   │   └── semantic_response.py # Pydantic схема ответа /api/chat/semantics
    │   └── files/                  # Оригиналы загруженных документов
    └── frontend/
        └── frontend-proto/
            ├── src/
            │   ├── App.tsx         # Весь UI (один компонент)
            │   └── main.tsx        # React entry point
            └── package.json
```
