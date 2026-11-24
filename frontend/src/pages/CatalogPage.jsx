import { useEffect, useState } from "react";
import Skeleton from "../components/Skeleton";
import CardSkeleton from "../components/CardSkeleton";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";

const DIFFICULTY = { easy: "легко", medium: "средне", hard: "сложно" };

export default function CatalogPage() {
  const { user, openAuth } = useAuth();
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [sort, setSort] = useState("new");
  const [page, setPage] = useState(1);
  const [categories, setCategories] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [data, setData] = useState({ items: [], total: 0, pages: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setSuggestions([]);
      return;
    }
    api(`/search/suggest?q=${encodeURIComponent(query.trim())}`)
      .then((result) => setSuggestions(result.items))
      .catch(() => {});
  }, [query]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    if (difficulty) params.set("difficulty", difficulty);
    params.set("sort", sort);
    params.set("page", page);
    setLoading(true);
    setError("");
    api(`/instructions?${params}`)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [q, category, difficulty, sort, page]);

  function search(event) {
    event.preventDefault();
    setPage(1);
    setQ(query.trim());
  }

  function setCat(id) {
    setCategory(String(id));
    setPage(1);
  }

  return (
    <>
      <section className="hero">
        <h1>Создавай и проходи <span>интерактивные инструкции</span> шаг за шагом</h1>
        <p>
          Сложные задачи превращаются в понятные чек-листы. Делись опытом,
          помогай другим и находи узкие места в своих гайдах.
        </p>
        <div className="hero-actions">
          <Link to={user ? "/dashboard/new" : "/register"} className="btn btn-primary">
            Стать автором
          </Link>
          {user ? (
            <Link to="/dashboard" className="btn btn-outline">Мои инструкции</Link>
          ) : (
            <button type="button" className="btn btn-outline" onClick={() => openAuth("login")}>Войти</button>
          )}
          <Link to="/download" className="btn btn-outline">
            <Icon name="download" size={16} /> Установить приложение
          </Link>
        </div>
      </section>

      <div className="search-section">
        <form onSubmit={search}>
          <input
            list="titles"
            className="search-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Умный поиск: что вы хотите сделать сегодня?"
          />
          <datalist id="titles">
            {suggestions.map((title) => <option key={title} value={title} />)}
          </datalist>
        </form>
        <div className="tags">
          <div className={`tag ${!category ? "active" : ""}`} onClick={() => setCat("")}>Все</div>
          {categories.map((item) => (
            <div
              key={item.id}
              className={`tag ${category === String(item.id) ? "active" : ""}`}
              onClick={() => setCat(item.id)}
            >
              {item.name}
            </div>
          ))}
        </div>
      </div>

      <div className="section-head">
        <h2>Популярные инструкции</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <select className="form-control w-auto" value={difficulty} onChange={(event) => { setDifficulty(event.target.value); setPage(1); }}>
            <option value="">Любая сложность</option>
            <option value="easy">Легко</option>
            <option value="medium">Средне</option>
            <option value="hard">Сложно</option>
          </select>
          <select className="form-control w-auto" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1); }}>
            <option value="new">Новые</option>
            <option value="rating">По рейтингу</option>
            <option value="popular">Популярные</option>
          </select>
          <span className="muted">Найдено: {data.total}</span>
        </div>
      </div>

      {loading && <CardSkeleton />}
      {error && <p className="error">{error}</p>}
      {!loading && !error && data.items.length === 0 && <p className="muted">Ничего не нашлось.</p>}

      <div className="grid">
        {data.items.map((item) => (
          <Link key={item.id} to={`/i/${item.id}`} className="card">
            <div className="card-header">
              <div className="card-title">{item.title}</div>
              {item.verified_at ? (
                <span className="badge expert">Эксперт</span>
              ) : item.forked_from_id ? (
                <span className="badge">Форк</span>
              ) : (
                <span className="badge">{item.category?.name || "Инструкция"}</span>
              )}
            </div>
            <p className="muted mb-12">{item.summary}</p>
            <div className="card-meta">
              <span className="stars"><Icon name="star" size={14} /> {item.rating_avg}</span>
              <span>{DIFFICULTY[item.difficulty] || item.difficulty}</span>
              <span>{item.minutes} мин</span>
              <span>{item.steps_count} шагов</span>
              <span>{item.views} просмотров</span>
            </div>
          </Link>
        ))}
      </div>

      {data.pages > 1 && (
        <div className="section-head mt-24">
          <button className="btn btn-outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Назад</button>
          <span className="muted">{page} / {data.pages}</span>
          <button className="btn btn-outline" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Вперёд</button>
        </div>
      )}
    </>
  );
}
