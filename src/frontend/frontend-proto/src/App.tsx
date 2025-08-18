import React, { useState } from "react";
import FileUpload from "./components/FileUpload";

type Reference = { title?: string; url: string };

type QAResponse = {
  answer: string;
  references?: Reference[];
};

export default function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [refs, setRefs] = useState<Reference[]>([]); // всегда массив
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading || text.trim() === "") return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    setRefs([]);

    try {
      const res = await fetch("http://192.168.162.178:8081/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ "question": text }) // здесь клю
      });

      if (!res.ok) throw new Error(`Ошибка ${res.status}`);

      const data: QAResponse = await res.json();
      setAnswer(data.answer);
      setRefs(data.references ?? []); // гарантируем массив
    } catch (err: any) {
      setError(err?.message || "Ошибка запроса");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
      <div className="app">
        <div className="card">
          <h1 className="title">WARHAMMER</h1>

          <form className="inputRow" onSubmit={handleSubmit}>
            <label htmlFor="q" className="visuallyHidden">Вопрос</label>
            <input
                id="q"
                type="text"
                autoComplete="off"
                placeholder="Сформулируйте вопрос"
                value={text}
                onChange={(e) => setText(e.target.value)}
                aria-invalid={!!error}
                aria-describedby={error ? "err" : undefined}
            />
            <button
                type="submit"
                disabled={loading || text.trim() === ""}
            >
              {loading ? "Отправка…" : "Отправить"}
            </button>
          </form>

          {loading && <div className="hint" aria-live="polite">Обработка запроса</div>}
          {error && <div className="error" id="err" role="alert">{error}</div>}
          {answer && (
              <div className="bubble">
                <p>{answer}</p>
                {refs.length > 0 && (
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

          <FileUpload />
        </div>
      </div>
  );
}
