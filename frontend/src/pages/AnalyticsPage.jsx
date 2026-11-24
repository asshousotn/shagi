import { useEffect, useState } from "react";
import Skeleton from "../components/Skeleton";
import CardSkeleton from "../components/CardSkeleton";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useToast } from "../toast";
import Icon from "../components/Icon";

export default function AnalyticsPage() {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [versions, setVersions] = useState([]);
  const [coachStep, setCoachStep] = useState(null);
  const [coach, setCoach] = useState(null);
  const [coachBusy, setCoachBusy] = useState(false);
  const { showToast } = useToast();

  async function load() {
    setError("");
    try {
      const [analytics, versionData] = await Promise.all([
        api(`/instructions/${id}/analytics`),
        api(`/instructions/${id}/versions`)
      ]);
      setData(analytics);
      setVersions(versionData);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function resolve(commentId) {
    try {
      await api(`/comments/${commentId}/resolve`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function runCoach() {
    if (!coachStep) return;
    setCoachBusy(true);
    setError("");
    try {
      setCoach(await api(`/instructions/${id}/ai-coach`, {
        method: "POST",
        body: JSON.stringify({ step_id: Number(coachStep) })
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setCoachBusy(false);
    }
  }

  async function applyCoach() {
    if (!coach || !coachStep) return;
    try {
      await api(`/instructions/${id}/ai-coach/apply`, {
        method: "POST",
        body: JSON.stringify({
          step_id: Number(coachStep),
          body: coach.rewrite,
          message: "Правка после разбора узкого места"
        })
      });
      showToast("Правка применена, создана версия");
      setCoach(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function rollback(versionId) {
    try {
      await api(`/instructions/${id}/versions/${versionId}/rollback`, { method: "POST" });
      showToast("Версия восстановлена");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!data) return <CardSkeleton count={4} />;

  return (
    <>
      <div className="section-head">
        <div>
          <h1 className="mb-8">Аналитика: {data.instruction.title}</h1>
          <p className="muted">Находите узкие места и помогайте пользователям дойти до конца.</p>
        </div>
        <div className="row gap-12">
          <Link to={`/i/${id}`} className="btn btn-outline">К инструкции</Link>
          <Link to={`/dashboard/${id}/edit`} className="btn btn-primary">Редактировать</Link>
        </div>
      </div>

      <div className="grid mb-24">
        <div className="card"><div className="muted">Начали</div><h2>{data.starts}</h2></div>
        <div className="card"><div className="muted">Завершили</div><h2>{data.finishes}</h2></div>
        <div className="card"><div className="muted">Completion rate</div><h2>{data.completion_rate}%</h2></div>
        <div className="card"><div className="muted">Рейтинг</div><h2>★ {data.rating_avg}</h2></div>
      </div>

      <div className="chart-box">
        <div className="section-head">
          <h3>Воронка прохождения</h3>
          <span className="badge">{data.starts} прохождений</span>
        </div>
        <div className="bar-chart">
          {data.steps.map((step) => {
            const completion = Math.max(0, 100 - step.dropoff_pct);
            const warning = step.step_id === data.bottleneck_step_id;
            return (
              <div className="bar-wrapper" key={step.step_id}>
                <div className="bar-tooltip" style={{ color: warning ? "var(--danger)" : "inherit" }}>{completion}%</div>
                <div className={`bar ${warning ? "warning" : ""}`} style={{ height: `${completion}%` }} />
                <div className="bar-label" style={{ color: warning ? "var(--danger)" : "inherit", fontWeight: warning ? 700 : 400 }}>
                  Шаг {step.position + 1}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {data.bottleneck_title && (
        <div className="alert-box mb-24">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <div>
            <b>Внимание! Узкое место.</b><br />
            Больше всего пользователей бросают инструкцию на шаге «{data.bottleneck_title}».
            Проверьте комментарии к шагу, добавьте фото или разбейте шаг на части.
          </div>
        </div>
      )}

      <div className="chart-box">
        <div className="section-head">
          <h3>ИИ-разбор шага</h3>
          <span className="badge">OpenRouter</span>
        </div>
        <div className="row gap-12 mt-16">
          <select
            className="form-control w-auto"
            value={coachStep || ""}
            onChange={(event) => setCoachStep(event.target.value)}
          >
            <option value="">Выберите шаг</option>
            {data.steps.map((step) => (
              <option key={step.step_id} value={step.step_id}>Шаг {step.position + 1}. {step.title}</option>
            ))}
          </select>
          <button className="btn btn-ai" onClick={runCoach} disabled={!coachStep || coachBusy}>
            <Icon name="spark" size={16} /> {coachBusy ? "Разбираем..." : "Разобрать"}
          </button>
        </div>
        {coach && (
          <div className="card mt-16">
            <h4 className="mb-8">Почему застревают</h4>
            <ul className="mb-16">
              {(coach.causes || []).map((cause, index) => <li key={index}>{cause}</li>)}
            </ul>
            <h4 className="mb-8">Как переписать шаг</h4>
            <p className="muted mb-16">{coach.rewrite}</p>
            <button className="btn btn-primary" onClick={applyCoach}>Применить и создать версию</button>
            {!coach.ai && <p className="muted mt-8">ИИ недоступен, показан шаблон.</p>}
          </div>
        )}
      </div>

      <div className="chart-box">
        <h3>Детали по шагам</h3>
        <table className="mt-16">
          <thead><tr><th>№</th><th>Шаг</th><th>Дошли</th><th>Завершили</th><th>Застряли</th><th>Отвал</th><th>Время</th><th>Комментарии</th><th>Реакции</th></tr></thead>
          <tbody>
            {data.steps.map((step) => (
              <tr key={step.step_id} className={step.step_id === data.bottleneck_step_id ? "bottleneck" : ""}>
                <td>{step.position + 1}</td>
                <td>{step.title}</td>
                <td>{step.reached}</td>
                <td>{step.completed}</td>
                <td>{step.stuck}</td>
                <td>{step.dropoff_pct}%</td>
                <td>{step.avg_seconds} с / {step.median_seconds} с</td>
                <td>{step.comments} / предл. {step.suggestions}</td>
                <td>+{step.likes} / -{step.dislikes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="chart-box">
        <h3>Предложения пользователей</h3>
        {data.suggestions.length === 0 && <p className="muted mt-12">Открытых предложений нет.</p>}
        <div className="comment-list" style={{ maxHeight: "none", marginTop: 16 }}>
          {data.suggestions.map((suggestion) => (
            <div className="comment-item" key={suggestion.id}>
              <div className="comment-avatar">{suggestion.user[0]}</div>
              <div className="comment-body">
                <div className="comment-author">{suggestion.user} · {suggestion.step_title || "общий комментарий"}</div>
                <div>{suggestion.body}</div>
                <button className="btn btn-outline mt-8" onClick={() => resolve(suggestion.id)}>Отметить решённым</button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="chart-box">
        <h3>Форки</h3>
        {data.forks.length === 0 && <p className="muted mt-12">Форков пока нет.</p>}
        <div className="grid mt-16">
          {data.forks.map((fork) => (
            <Link key={fork.id} to={`/i/${fork.id}`} className="card">
              <div className="card-title">{fork.title}</div>
              <div className="card-meta"><span>★ {fork.rating_avg}</span><span>{fork.author}</span><span>{fork.completion_rate}%</span></div>
            </Link>
          ))}
        </div>
      </div>

      <div className="chart-box mt-24">
        <div className="section-head">
          <h3>История версий</h3>
          <Icon name="history" size={18} />
        </div>
        {versions.length === 0 && <p className="muted mt-12">Версий пока нет — они создаются при принятии правок и ИИ-исправлениях.</p>}
        <div className="mt-16">
          {versions.map((version) => (
            <div className="card mb-12" key={version.id}>
              <div className="card-header">
                <div className="card-title">Версия {version.number}</div>
                <span className="muted">{new Date(version.created_at).toLocaleString("ru-RU")}</span>
              </div>
              <p className="muted mb-8">{version.message || "Без сообщения"}</p>
              {version.author && <p className="muted mb-8">Автор: {version.author.name}</p>}
              <p className="muted mb-8">Шагов: {version.steps.length}</p>
              <button className="btn btn-outline" onClick={() => rollback(version.id)}>Откатить к этой версии</button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
