import { useEffect, useRef, useState } from "react";
import Skeleton from "../components/Skeleton";
import { Link, useParams } from "react-router-dom";
import { api, assetUrl, track } from "../api";
import { useAuth } from "../auth";
import ProgressBar from "../components/ProgressBar";
import Icon from "../components/Icon";

export default function RunPage({ embedded = false }) {
  const { id } = useParams();
  const { user, openAuth } = useAuth();
  const [item, setItem] = useState(null);
  const [index, setIndex] = useState(0);
  const [completed, setCompleted] = useState(new Set());
  const [checked, setChecked] = useState(false);
  const [finished, setFinished] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [commentKind, setCommentKind] = useState("comment");
  const [commentNotice, setCommentNotice] = useState("");
  const [stuckNotice, setStuckNotice] = useState("");
  const startedRef = useRef(Date.now());

  useEffect(() => {
    let alive = true;
    setReady(false);
    setError("");
    Promise.all([api(`/instructions/${id}`), api(`/progress/${id}`)])
      .then(async ([detail, progress]) => {
        if (!alive) return;
        const done = new Set(progress.completed_step_ids);
        const firstOpen = detail.steps.findIndex((step) => !done.has(step.id));
        setItem(detail);
        setCompleted(done);
        setIndex(firstOpen >= 0 ? firstOpen : Math.max(detail.steps.length - 1, 0));
        setChecked(firstOpen >= 0 ? done.has(detail.steps[firstOpen].id) : true);
        setFinished(progress.finished || firstOpen < 0);
        if (!localStorage.getItem(`started:${id}`)) {
          localStorage.setItem(`started:${id}`, "1");
          await track("instruction_start", { instruction_id: detail.id });
        }
        setReady(true);
      })
      .catch((err) => {
        if (alive) setError(err.message);
      });
    return () => { alive = false; };
  }, [id]);

  const steps = item?.steps || [];
  const step = steps[index];

  useEffect(() => {
    if (!ready || finished || !item || !step) return;
    startedRef.current = Date.now();
    track("step_view", { instruction_id: item.id, step_id: step.id });
  }, [ready, finished, item?.id, step?.id]);

  async function goTo(nextIndex) {
    setIndex(nextIndex);
    setChecked(completed.has(steps[nextIndex].id));
    setNotice("");
  }

  async function complete() {
    if (!step) return;
    if (!checked && !completed.has(step.id)) return;
    if (!completed.has(step.id)) {
      await track("step_complete", {
        instruction_id: item.id,
        step_id: step.id,
        duration_ms: Date.now() - startedRef.current
      });
      const next = new Set(completed);
      next.add(step.id);
      setCompleted(next);
      if (index + 1 >= steps.length) {
        if (next.size >= steps.length) await track("instruction_complete", { instruction_id: item.id });
        setFinished(true);
        return;
      }
      await goTo(index + 1);
      return;
    }
    if (index + 1 >= steps.length) setFinished(true);
    else await goTo(index + 1);
  }

  async function skip() {
    if (!step) return;
    await track("step_skip", {
      instruction_id: item.id,
      step_id: step.id,
      duration_ms: Date.now() - startedRef.current
    });
    if (index + 1 >= steps.length) setFinished(true);
    else await goTo(index + 1);
  }

  async function markStuck() {
    if (!step) return;
    await track("step_stuck", {
      instruction_id: item.id,
      step_id: step.id,
      duration_ms: Date.now() - startedRef.current
    });
    setStuckNotice("Отметили. Автор увидит, где вы застряли.");
  }

  async function react(value) {
    const result = await api("/reactions", {
      method: "POST",
      body: JSON.stringify({ target_type: "step", target_id: step.id, value })
    });
    setItem({
      ...item,
      steps: item.steps.map((entry) => entry.id === step.id ? { ...entry, likes: result.likes, dislikes: result.dislikes } : entry)
    });
  }

  async function rate(score) {
    try {
      const result = await api(`/instructions/${id}/rating`, {
        method: "POST",
        body: JSON.stringify({ score })
      });
      setItem({ ...item, rating_avg: result.rating_avg, rating_count: result.rating_count, my_rating: result.my_rating });
      setNotice("Спасибо за оценку");
    } catch (err) {
      setError(err.message);
    }
  }

  async function sendComment(event) {
    event.preventDefault();
    if (!commentBody.trim() || !step) return;
    try {
      await api(`/instructions/${id}/comments`, {
        method: "POST",
        body: JSON.stringify({ body: commentBody.trim(), step_id: step.id, kind: commentKind })
      });
      setCommentBody("");
      setCommentNotice("Комментарий отправлен");
    } catch (err) {
      setCommentNotice(err.message);
    }
  }

  if (error && !item) return <p className="error">{error}</p>;
  if (!item) return <Skeleton />;

  if (finished) {
    const allDone = completed.size >= steps.length;
    return (
      <div className={`hero ${embedded ? "embed" : ""}`}>
        <h1>{allDone ? "Готово" : "Прохождение завершено"}</h1>
        <p>
          {allDone ? "Все шаги отмечены. Можно оценить инструкцию." : `Отмечено ${completed.size} из ${steps.length} шагов.`}
        </p>
        <div style={{ maxWidth: 400, margin: "24px auto" }}>
          <ProgressBar value={steps.length ? (completed.size / steps.length) * 100 : 0} />
        </div>
        <div className="hero-actions">
          {[1, 2, 3, 4, 5].map((score) => (
            <button key={score} className="btn btn-outline" disabled={item.my_rating === score} onClick={() => rate(score)}>{score}</button>
          ))}
        </div>
        {notice && <p className="muted">{notice}</p>}
        <div className="hero-actions mt-24">
          <Link to={`/i/${item.id}`} className="btn btn-primary">Вернуться к инструкции</Link>
          <Link to="/" className="btn btn-outline">В каталог</Link>
        </div>
        {embedded && <p><a href={`/i/${item.id}/run`} target="_blank" rel="noreferrer">Открыть на сайте</a></p>}
      </div>
    );
  }

  const percent = steps.length ? (completed.size / steps.length) * 100 : 0;

  return (
    <div className={embedded ? "embed" : ""}>
      <div className="instruction-layout">
        <div>
          {!embedded && <Link to={`/i/${item.id}`} className="btn btn-outline mb-24">← К инструкции</Link>}
          <h1 style={{ fontSize: 28, marginBottom: 24 }}>{item.title}</h1>

          {step && (
            <div className="step-item">
              <div className={`step-checkbox ${completed.has(step.id) ? "completed" : ""}`}>
                {completed.has(step.id) ? "✓" : index + 1}
              </div>
              <div className="step-content">
                <h4>Шаг {index + 1}. {step.title}</h4>
                <p className="muted mt-8">{step.body}</p>
                {step.image_url && <img src={assetUrl(step.image_url)} alt="" style={{ maxWidth: "100%", marginTop: 12, borderRadius: 12 }} />}
                {step.images.length > 0 && (
                  <div className="row gap-8 mt-8">
                    {step.images.map((image) => (
                      <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 140, height: 100, objectFit: "cover", borderRadius: 8 }} />
                    ))}
                  </div>
                )}
                <div className="form-group" style={{ marginTop: 20 }}>
                  <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input type="checkbox" checked={checked} onChange={(event) => setChecked(event.target.checked)} /> Шаг выполнен
                  </label>
                </div>
                <div className="step-actions">
                  <button className="btn btn-outline" disabled={index === 0} onClick={() => goTo(index - 1)}>Назад</button>
                  <button className="btn btn-primary" disabled={!checked && !completed.has(step.id)} onClick={complete}>
                    {index + 1 >= steps.length ? "Завершить" : "Далее"}
                  </button>
                  <button className="btn btn-outline" onClick={skip}>Пропустить</button>
                </div>
                <div className="step-actions">
                  <div className="action-btn" onClick={() => react(1)}><Icon name="up" size={14} /> Полезно ({step.likes})</div>
                  <div className="action-btn" onClick={() => react(-1)}><Icon name="down" size={14} /> ({step.dislikes})</div>
                  <div className="action-btn" onClick={markStuck}><Icon name="warning" size={14} /> Я застрял</div>
                </div>
                {stuckNotice && <p className="muted mt-8">{stuckNotice}</p>}

                <h3 style={{ marginTop: 24, fontSize: 16 }}>Комментарий к шагу</h3>
                {user ? (
                  <form onSubmit={sendComment} className="mt-12">
                    <textarea className="form-control" value={commentBody} onChange={(event) => setCommentBody(event.target.value)} placeholder="Что непонятно или как улучшить шаг" />
                    <div className="row gap-12 mt-12">
                      <select className="form-control w-auto" value={commentKind} onChange={(event) => setCommentKind(event.target.value)}>
                        <option value="comment">Комментарий</option>
                        <option value="suggestion">Предложение улучшения</option>
                      </select>
                      <button type="submit" className="btn btn-primary">Отправить</button>
                    </div>
                  </form>
                ) : (
                  <p className="muted"><button type="button" className="btn btn-outline" onClick={() => openAuth("login")}>Войти</button>, чтобы оставить комментарий.</p>
                )}
                {commentNotice && <p className="muted">{commentNotice}</p>}
              </div>
            </div>
          )}
          {error && <p className="error">{error}</p>}
        </div>

        <div>
          <div className="progress-box">
            <h3 style={{ marginBottom: 16, fontSize: 16 }}>Ваш прогресс</h3>
            <ProgressBar value={percent} />
            <p className="muted text-sm text-right">
              Шаг {index + 1} из {steps.length} · {completed.size} отмечено
            </p>
            <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }} />
            <Link to={`/i/${item.id}`} className="btn btn-outline w-full">К инструкции</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
