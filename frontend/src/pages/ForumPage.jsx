import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import Skeleton from "../components/Skeleton";
import CardSkeleton from "../components/CardSkeleton";
import AttachmentEditor from "../components/AttachmentEditor";
import { useToast } from "../toast";

export default function ForumPage() {
  const { user, openAuth } = useAuth();
  const { showToast } = useToast();
  const [params] = useSearchParams();
  const instructionId = params.get("instruction") || "";
  const [categories, setCategories] = useState([]);
  const [topics, setTopics] = useState([]);
  const [category, setCategory] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [topicImages, setTopicImages] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    const query = category ? `?category=${category}` : "";
    try {
      const [categoryData, topicData] = await Promise.all([
        api("/forum/categories"),
        api(`/forum/topics${query}`)
      ]);
      setCategories(categoryData);
      setTopics(topicData.items);
      if (!newCategory && categoryData.length) setNewCategory(String(categoryData[0].id));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [category]);

  async function create(event) {
    event.preventDefault();
    if (!user) return openAuth("login");
    try {
      await api("/forum/topics", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          body: body.trim(),
          category_id: Number(newCategory),
          instruction_id: instructionId ? Number(instructionId) : null,
          images: topicImages.map((image) => image.url || image)
        })
      });
      setTitle("");
      setBody("");
      setTopicImages([]);
      setCreating(false);
      showToast("Тема создана");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <div className="section-head mb-24">
        <div>
          <h1>Форум</h1>
          <p className="muted">Обсуждения, вопросы и предложения по инструкциям.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(!creating)}>
          <Icon name="plus" size={16} /> {creating ? "Закрыть" : "Новая тема"}
        </button>
      </div>

      {creating && (
        <form className="chart-box mb-24" onSubmit={create}>
          <div className="form-group">
            <label>Заголовок</label>
            <input className="form-control" value={title} onChange={(event) => setTitle(event.target.value)} required />
          </div>
          <div className="form-group">
            <label>Сообщение</label>
            <textarea className="form-control" value={body} onChange={(event) => setBody(event.target.value)} required />
          </div>
          <AttachmentEditor targetType="topic" targetId={null} attachments={topicImages} onChange={setTopicImages} label="Картинки к теме" />
          <div className="row gap-12">
            <select className="form-control w-auto" value={newCategory} onChange={(event) => setNewCategory(event.target.value)}>
              {categories.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
            </select>
            <button type="submit" className="btn btn-primary">Создать тему</button>
          </div>
          {instructionId && <p className="muted mt-8">Тема будет связана с инструкцией #{instructionId}</p>}
        </form>
      )}

      <div className="tags mb-24">
        <button type="button" className={`tag ${!category ? "active" : ""}`} onClick={() => setCategory("")}>Все</button>
        {categories.map((item) => (
          <button key={item.id} type="button" className={`tag ${category === String(item.id) ? "active" : ""}`} onClick={() => setCategory(String(item.id))}>
            {item.title}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <CardSkeleton count={5} />}
      {!loading && topics.length === 0 && <p className="muted">Тем пока нет. Создайте первую.</p>}
      {!loading && (
        <div style={{ display: "grid", gap: 12 }}>
          {topics.map((topic) => (
            <Link key={topic.id} to={`/forum/${topic.id}`} className="card">
              <div className="card-header">
                <div className="card-title">
                  {topic.pinned && <span className="badge mr-8">Закреплено</span>}
                  {topic.closed && <span className="badge mr-8">Закрыто</span>}
                  {topic.title}
                </div>
                <span className="muted">{new Date(topic.updated_at).toLocaleDateString("ru-RU")}</span>
              </div>
              <p className="muted mb-8">{topic.body.slice(0, 180)}</p>
              <div className="card-meta">
                <span>{topic.author.name}</span>
                <span><Icon name="chat" size={14} /> {topic.posts_count}</span>
                <span>{topic.views} просмотров</span>
                {topic.instruction_id && <Link to={`/i/${topic.instruction_id}`}>Инструкция #{topic.instruction_id}</Link>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
