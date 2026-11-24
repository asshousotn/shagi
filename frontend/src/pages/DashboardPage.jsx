import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import ProgressBar from "../components/ProgressBar";
import CardSkeleton from "../components/CardSkeleton";

const TABS = [
  ["instructions", "Инструкции"],
  ["analytics", "Аналитика"],
  ["progress", "Прохождения"],
  ["bookmarks", "Избранное"],
  ["inbox", "Предложения"],
  ["activity", "Активность"]
];

const EVENT_LABELS = {
  instruction_start: "Начал инструкцию",
  instruction_complete: "Завершил инструкцию",
  step_view: "Открыл шаг",
  step_complete: "Отметил шаг",
  step_skip: "Пропустил шаг"
};

export default function DashboardPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState("instructions");
  const [stats, setStats] = useState(null);
  const [items, setItems] = useState([]);
  const [progress, setProgress] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [inbox, setInbox] = useState([]);
  const [activity, setActivity] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setError("");
    setLoading(true);
    try {
      const [analytics, instructions, progressData, bookmarkData, inboxData, activityData] = await Promise.all([
        api("/me/analytics"),
        api("/me/instructions"),
        api("/me/progress"),
        api("/me/bookmarks"),
        api("/me/inbox"),
        api("/me/activity")
      ]);
      setStats(analytics);
      setItems(instructions.items);
      setProgress(progressData.items);
      setBookmarks(bookmarkData.items);
      setInbox(inboxData.items);
      setActivity(activityData.items);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function publish(id) {
    try {
      await api(`/instructions/${id}/publish`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function resolve(id) {
    try {
      await api(`/comments/${id}/resolve`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <CardSkeleton count={4} />;

  return (
    <>
      <div className="section-head mb-24">
        <div>
          <h1>Личный кабинет</h1>
          <p className="muted">{user?.name} · {user?.role === "expert" ? "Эксперт" : "Ученик"}</p>
        </div>
        <Link to="/dashboard/new" className="btn btn-ai"><Icon name="plus" size={16} /> Создать черновик</Link>
      </div>

      {stats && (
        <div className="grid mb-24">
          <div className="card"><div className="muted">Инструкций</div><h2>{stats.instructions}</h2></div>
          <div className="card"><div className="muted">Начали</div><h2>{stats.starts}</h2></div>
          <div className="card"><div className="muted">Завершили</div><h2>{stats.finishes}</h2></div>
          <div className="card"><div className="muted">Completion rate</div><h2>{stats.completion_rate}%</h2></div>
        </div>
      )}

      <div className="tags mb-24">
        {TABS.map(([key, label]) => (
          <button key={key} type="button" className={`tag ${tab === key ? "active" : ""}`} onClick={() => setTab(key)}>
            {label}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {tab === "instructions" && (
        <div className="chart-box">
          <h3 className="mb-16">Мои инструкции ({items.length})</h3>
          {items.length === 0 && <p className="muted">Пока нет инструкций.</p>}
          <div style={{ display: "grid", gap: 16 }}>
            {items.map((item) => (
              <div className="card" key={item.id}>
                <div className="card-header">
                  <Link to={`/i/${item.id}`} className="card-title">{item.title}</Link>
                  <span className={`badge ${item.status === "draft" ? "draft" : ""}`}>
                    {item.status === "published" ? "Опубликована" : "Черновик"}
                  </span>
                </div>
                <div className="card-meta">
                  <span>{item.views} просмотров</span>
                  <span>{item.starts} начали</span>
                  <span>{item.completion_rate}% завершили</span>
                  <span className="stars"><Icon name="star" size={14} /> {item.rating_avg} ({item.rating_count})</span>
                </div>
                <div className="row gap-12 mt-12">
                  <Link to={`/dashboard/${item.id}/edit`} className="btn btn-outline">Редактировать</Link>
                  <Link to={`/dashboard/${item.id}/analytics`} className="btn btn-outline">Аналитика</Link>
                  {item.status === "draft" && <button className="btn btn-primary" onClick={() => publish(item.id)}>Опубликовать</button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "analytics" && (
        <div className="chart-box">
          <h3 className="mb-16">Сводка по инструкциям</h3>
          {stats?.items?.map((item) => (
            <Link key={item.id} to={`/dashboard/${item.id}/analytics`} className="card mb-12" style={{ display: "block" }}>
              <div className="card-title mb-8">{item.title}</div>
              <div className="card-meta">
                <span>{item.starts} начали</span>
                <span>{item.completion_rate}% завершили</span>
                <span className="stars"><Icon name="star" size={14} /> {item.rating_avg}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {tab === "progress" && (
        <div className="chart-box">
          <h3 className="mb-16">Мои прохождения</h3>
          {progress.length === 0 && <p className="muted">Вы ещё не начинали инструкции.</p>}
          {progress.map((item) => (
            <Link key={item.instruction_id} to={`/i/${item.instruction_id}/run`} className="card mb-12" style={{ display: "block" }}>
              <div className="card-title mb-8">{item.title}</div>
              <ProgressBar value={item.percent} />
              <div className="card-meta"><span>{item.completed} из {item.total} шагов</span><span>{item.percent}%</span></div>
            </Link>
          ))}
        </div>
      )}

      {tab === "bookmarks" && (
        <div className="chart-box">
          <h3 className="mb-16">Избранное</h3>
          {bookmarks.length === 0 && <p className="muted">Пока пусто.</p>}
          <div className="grid">
            {bookmarks.map((item) => (
              <Link key={item.id} to={`/i/${item.id}`} className="card">
                <div className="card-title mb-8">{item.title}</div>
                <div className="card-meta"><span className="stars"><Icon name="star" size={14} /> {item.rating_avg}</span><span>{item.steps_count} шагов</span></div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {tab === "inbox" && (
        <div className="chart-box">
          <h3 className="mb-16">Предложения пользователей</h3>
          {inbox.length === 0 && <p className="muted">Новых предложений нет.</p>}
          {inbox.map((item) => (
            <div className="card mb-12" key={item.id}>
              <div className="card-title mb-8">
                <Link to={`/i/${item.instruction_id}`}>{item.instruction_title}</Link>
                {item.step_title && <span className="muted"> · {item.step_title}</span>}
              </div>
              <p className="muted mb-8">{item.body}</p>
              <div className="row gap-12">
                <span className="muted">{item.user}</span>
                <button className="btn btn-outline" onClick={() => resolve(item.id)}>Решено</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "activity" && (
        <div className="chart-box">
          <h3 className="mb-16">Журнал активности</h3>
          {activity.length === 0 && <p className="muted">Пока нет событий.</p>}
          {activity.map((item, index) => (
            <div className="row gap-12 mb-12" key={index} style={{ justifyContent: "space-between" }}>
              <span>{EVENT_LABELS[item.type] || item.type}</span>
              <Link to={`/i/${item.instruction_id}`} className="muted">{item.instruction_title}</Link>
              <span className="muted">{new Date(item.created_at).toLocaleString("ru-RU")}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
