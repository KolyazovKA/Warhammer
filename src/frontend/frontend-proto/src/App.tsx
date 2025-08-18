import React, { useState } from "react";
import FileUpload from "./components/FileUpload";

type QAResponse = {
  answer: string;
  references?: { title: string; url: string }[];
};

// const API_BASE = "/api";

export default function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [refs] = useState<QAResponse["references"]>([]);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const res = await fetch("/api/test"); // GET запрос на бек
      if (!res.ok) throw new Error(`Ошибка ${res.status}`);

      const data = await res.text(); // или res.json() если бек возвращает JSON
      console.log(data);
      setAnswer(data); // отображаем ответ в bubble
    } catch (err: any) {
      setError(err?.message || "Ошибка запроса");
      console.log(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <div className="card">
        <h1 className="title">WARHAMMER</h1>

        {/* Форма для ввода вопроса */}
        <form className="inputRow" onSubmit={handleSubmit}>
          <label htmlFor="q" className="visuallyHidden">
            Вопрос
          </label>
          <input
            id="q"
            type="text"
            inputMode="text"
            autoComplete="off"
            placeholder="Сформулируйте вопрос"
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "err" : undefined}
          />
          <button
            type="submit"
            className="sendBtn"
            disabled={loading || text.trim().length === 0}
          >
            {loading ? "Отправка…" : "Отправить"}
          </button>
        </form>

        {loading && (
          <div className="hint" aria-live="polite">
            Обработка запроса
          </div>
        )}
        {error && (
          <div className="error" id="err" role="alert">
            {error}
          </div>
        )}
        {answer && (
          <div className="bubble">
            <p>{answer}</p>
            {refs && refs.length > 0 && (
              <div className="refs">
                {refs.map((r, i) => (
                  <a key={i} href={r.url} target="_blank" rel="noreferrer">
                    {r.title || r.url}
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Загрузка файлов */}
        <FileUpload />
      </div>
    </div>
  );
}
