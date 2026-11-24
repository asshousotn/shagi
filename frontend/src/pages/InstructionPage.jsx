import { useEffect, useState } from "react";
import Skeleton from "../components/Skeleton";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, assetUrl } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../toast";
import Comments from "../components/Comments";
import ProgressBar from "../components/ProgressBar";
import Icon from "../components/Icon";

export default function InstructionPage() {
  const { id } = useParams();
  const { user, openAuth } = useAuth();
  const { showToast, ask } = useToast();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [comments, setComments] = useState([]);
  const [forks, setForks] = useState([]);
  const [topics, setTopics] = useState([]);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function loadComments() {
    setComments(await api(`/instructions/${id}/comments`));
  }

  async function load() {
    setError("");
    try {
      const [detail, commentData, forkData, progressData, topicData] = await Promise.all([
        api(`/instructions/${id}`),
        api(`/instructions/${id}/comments`),
        api(`/instructions/${id}/forks`),
        api(`/progress/${id}`),
        api(`/forum/instructions/${id}/topics`)
      ]);
      setItem(detail);
      setComments(commentData);
      setForks(forkData.items);
      setProgress(progressData);
      setTopics(topicData.items);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id, user?.id]);

  async function bookmark() {
    if (!user) return openAuth("login");
    const result = await api(`/instructions/${id}/bookmark`, { method: "POST" });
    setItem({ ...item, bookmarked: result.bookmarked });
  }

  async function rate(score) {
    const result = await api(`/instructions/${id}/rating`, {
      method: "POST",
      body: JSON.stringify({ score })
    });
    setItem({ ...item, ...result });
  }

  async function react(value) {
    const result = await api("/reactions", {
      method: "POST",
      body: JSON.stringify({ target_type: "instruction", target_id: item.id, value })
    });
    setItem({ ...item, likes: result.likes, dislikes: result.dislikes });
  }

  async function fork() {
    if (!user) return openAuth("login");
    try {
      const copy = await api(`/instructions/${id}/fork`, { method: "POST" });
      navigate(`/dashboard/${copy.id}/edit`);
    } catch (err) {
      setError(err.message);
    }
  }

  async function publish() {
    try {
      await api(`/instructions/${id}/publish`, { method: "POST" });
      await load();
      setNotice("Инструкция опубликована");
    } catch (err) {
      setError(err.message);
    }
  }

  async function verify() {
    try {
      await api(`/instructions/${id}/verify`, {
        method: item.verified_at ? "DELETE" : "POST"
      });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function report() {
    if (!user) return openAuth("login");
    if (!(await ask("Пожаловаться на инструкцию?"))) return;
    try {
      await api("/admin/reports", {
        method: "POST",
        body: JSON.stringify({ target_type: "instruction", target_id: item.id, reason: "Жалоба пользователя" })
      });
      showToast("Жалоба отправлена");
    } catch (err) {
      setError(err.message);
    }
  }

  async function copyEmbed() {
    const code = `<iframe src="${window.location.origin}/embed/${id}" width="100%" height="700" style="border:0"></iframe>`;
    try {
      await navigator.clipboard.writeText(code);
      showToast("Код вставки скопирован");
    } catch {
      window.prompt("Скопируйте код", code);
    }
  }

  if (error && !item) return <p className="error">{error}</p>;
  if (!item) return <Skeleton />;

  const canEdit = user?.id === item.author.id;
  const done = new Set(progress?.completed_step_ids || []);
  const completed = progress?.completed_count || done.size;

  return (
    <>
      <Link to="/" className="btn btn-outline mb-24">← Назад в каталог</Link>

      <div className="instruction-layout">
        <div>
          <h1 style={{ fontSize: 32, marginBottom: 8 }}>{item.title}</h1>
          <p className="muted mb-32">
            Автор: <Link to={`/u/${item.author.id}`}><b>{item.author.name}</b></Link>
            {item.verified_at && <span className="badge expert" style={{ marginLeft: 8 }}>Эксперт</span>}
            {item.forked_from_id && <span className="badge" style={{ marginLeft: 8 }}>Форк</span>}
          </p>
          <p className="muted mb-24">{item.summary}</p>
          <p className="mb-24">
            {item.tags.map((tag) => <span key={tag.id} className="badge" style={{ marginRight: 6 }}>#{tag.name}</span>)}
          </p>

          {item.images.length > 0 && (
            <div className="row gap-8 mb-24">
              {item.images.map((image) => (
                <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 160, height: 110, objectFit: "cover", borderRadius: 10 }} />
              ))}
            </div>
          )}

          {item.steps.map((step, index) => (
            <div className="step-item" key={step.id}>
              <div className={`step-checkbox ${done.has(step.id) ? "completed" : ""}`}>
                {done.has(step.id) ? "✓" : index + 1}
              </div>
              <div className="step-content">
                <h4>Шаг {index + 1}. {step.title}</h4>
                <p className="muted">{step.body}</p>
                {step.image_url && <img src={assetUrl(step.image_url)} alt="" style={{ maxWidth: "100%", marginTop: 12, borderRadius: 12 }} />}
                {step.images.length > 0 && (
                  <div className="row gap-8 mt-8">
                    {step.images.map((image) => (
                      <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 120, height: 90, objectFit: "cover", borderRadius: 8 }} />
                    ))}
                  </div>
                )}
                <div className="step-actions">
                  <div className="action-btn" onClick={() => api("/reactions", { method: "POST", body: JSON.stringify({ target_type: "step", target_id: step.id, value: 1 }) }).then((r) => setItem({ ...item, steps: item.steps.map((s) => s.id === step.id ? { ...s, likes: r.likes, dislikes: r.dislikes } : s) }))}>
                    <Icon name="up" size={14} /> Полезно ({step.likes})
                  </div>
                  <div className="action-btn" onClick={() => api("/reactions", { method: "POST", body: JSON.stringify({ target_type: "step", target_id: step.id, value: -1 }) }).then((r) => setItem({ ...item, steps: item.steps.map((s) => s.id === step.id ? { ...s, likes: r.likes, dislikes: r.dislikes } : s) }))}>
                    <Icon name="down" size={14} /> ({step.dislikes})
                  </div>
                  <a className="comments-btn" href="#comments"><Icon name="chat" size={14} /> {comments.filter((c) => c.step_id === step.id).length} комментариев</a>
                </div>
              </div>
            </div>
          ))}

          <div className="chart-box" id="rating">
            <h3>Оценка инструкции</h3>
            <p className="muted" style={{ margin: "12px 0" }}>
              <Icon name="star" size={14} /> {item.rating_avg} ({item.rating_count}) · полезно {item.likes} / не полезно {item.dislikes}
            </p>
            <div className="row gap-8">
              {[1, 2, 3, 4, 5].map((score) => (
                <button key={score} className="btn btn-outline" disabled={item.my_rating === score} onClick={() => rate(score)}>{score}</button>
              ))}
              <button className="btn btn-outline" onClick={() => react(1)}>Полезно</button>
              <button className="btn btn-outline" onClick={() => react(-1)}>Не полезно</button>
            </div>
          </div>
          {notice && <p>{notice}</p>}
          {error && <p className="error">{error}</p>}
        </div>

        <div>
          <div className="progress-box">
            <h3 style={{ marginBottom: 16, fontSize: 16 }}>Ваш прогресс</h3>
            <ProgressBar value={item.steps.length ? (completed / item.steps.length) * 100 : 0} />
            <p className="muted text-sm text-right">Выполнено {completed} из {item.steps.length}</p>
            <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }} />
            <Link to={`/i/${item.id}/run`} className="btn btn-primary w-full mb-10">
              {completed ? "Продолжить" : "Начать прохождение"}
            </Link>
            <Link to={`/i/${item.id}/print`} className="btn btn-outline w-full mb-10"><Icon name="download" size={16} /> Скачать в PDF</Link>
            <button className="btn btn-outline w-full mb-10" onClick={copyEmbed}>Embed</button>
            <button type="button" className="action-link" onClick={report}>Пожаловаться</button>
            {user && <button className="btn btn-outline w-full mb-10" onClick={bookmark}>{item.bookmarked ? "Убрать из избранного" : "В избранное"}</button>}
            {user && <button className="btn btn-outline w-full mb-10" onClick={fork}><Icon name="branch" size={16} /> Улучшить (форк)</button>}
            {canEdit && <Link to={`/dashboard/${item.id}/edit`} className="btn btn-outline w-full mb-10">Редактировать</Link>}
            {canEdit && <Link to={`/dashboard/${item.id}/analytics`} className="btn btn-outline w-full mb-10">Аналитика</Link>}
            {canEdit && item.status === "draft" && <button className="btn btn-primary w-full" onClick={publish}>Опубликовать</button>}
            {user?.role === "expert" && <button className="btn btn-ai" style={{ width: "100%", marginTop: 10 }} onClick={verify}>{item.verified_at ? "Снять проверку" : "Проверить как эксперт"}</button>}
          </div>
        </div>
      </div>

      {forks.length > 0 && (
        <div className="chart-box mt-24">
          <h3>Форки</h3>
          <div className="grid mt-16">
            {forks.map((fork) => (
              <Link key={fork.id} to={`/i/${fork.id}`} className="card">
                <div className="card-title">{fork.title}</div>
                <div className="card-meta"><span className="stars"><Icon name="star" size={14} /> {fork.rating_avg}</span><span>{fork.author.name}</span><span>{fork.completion_rate}%</span></div>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="chart-box mt-24">
        <div className="section-head">
          <h3>Обсуждение на форуме</h3>
          <Link to={`/forum?instruction=${item.id}`} className="action-link">Создать тему</Link>
        </div>
        {topics.length === 0 && <p className="muted mt-12">Тем пока нет.</p>}
        {topics.map((topic) => (
          <Link key={topic.id} to={`/forum/${topic.id}`} className="card mt-12" style={{ display: "block" }}>
            <div className="card-title mb-8">{topic.title}</div>
            <div className="card-meta"><span>{topic.author.name}</span><span><Icon name="chat" size={14} /> {topic.posts_count}</span><span>{new Date(topic.updated_at).toLocaleDateString("ru-RU")}</span></div>
          </Link>
        ))}
      </div>

      <div id="comments" style={{ marginTop: 32 }}>
        <Comments instructionId={item.id} comments={comments} steps={item.steps} onRefresh={loadComments} canResolve={canEdit} />
      </div>
    </>
  );
}
