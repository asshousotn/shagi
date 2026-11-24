import { useEffect, useRef, useState } from "react";
import Skeleton from "../components/Skeleton";
import { Link, useParams } from "react-router-dom";
import { api, assetUrl } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import { useModalFocus } from "../useModalFocus";

export default function ProfilePage() {
  const { id } = useParams();
  const { user, updateProfile } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [editOpen, setEditOpen] = useState(false);
  const [name, setName] = useState("");
  const [bio, setBio] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const modalRef = useRef(null);
  useModalFocus(editOpen, modalRef, () => setEditOpen(false));

  useEffect(() => {
    setError("");
    api(`/users/${id}`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id]);

  function openEdit() {
    setName(data.user.name);
    setBio(data.user.bio);
    setAvatarUrl(data.user.avatar_url || "");
    setEditOpen(true);
  }

  async function uploadAvatar(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/uploads", { method: "POST", body: form });
      setAvatarUrl(result.url);
    } catch (err) {
      setError(err.message);
    }
  }

  async function save() {
    setBusy(true);
    setError("");
    try {
      const updated = await updateProfile({
        name: name.trim(),
        bio: bio.trim(),
        avatar_url: avatarUrl
      });
      setData({ ...data, user: { ...data.user, ...updated } });
      setEditOpen(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p className="error">{error}</p>;
  if (!data) return <Skeleton />;

  const own = user?.id === data.user.id;

  return (
    <>
      <div className="dashboard-grid mb-24">
        <div className="profile-card">
          {data.user.avatar_url ? (
            <img src={assetUrl(data.user.avatar_url)} alt="" className="avatar" style={{ objectFit: "cover", margin: "0 auto 16px", width: 80, height: 80 }} />
          ) : (
            <div className="avatar">{data.user.name[0]}</div>
          )}
          <h3>{data.user.name}</h3>
          <p className="muted mb-16">{data.user.role === "expert" ? "Эксперт" : "Ученик"}</p>
          <p className="muted">{data.user.bio}</p>
          {own && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center", marginTop: 16 }}>
              <button className="btn btn-outline" onClick={openEdit}>Редактировать профиль</button>
              <Link to="/dashboard" className="btn btn-outline">Мои инструкции</Link>
            </div>
          )}
        </div>
        <div className="chart-box">
          <h3 className="mb-16">Статистика</h3>
          <div className="grid">
            <div className="card"><div className="muted">Инструкций</div><h2>{data.stats.instructions}</h2></div>
            <div className="card"><div className="muted">Просмотров</div><h2>{data.stats.views}</h2></div>
            <div className="card"><div className="muted">Средний рейтинг</div><h2 className="stars"><Icon name="star" size={16} /> {data.stats.rating_avg}</h2></div>
          </div>
        </div>
      </div>

      <div className="section-head mb-16">
        <h2>Инструкции</h2>
        {own && <Link to="/dashboard/new" className="btn btn-ai"><Icon name="plus" size={16} /> Новая инструкция</Link>}
      </div>
      {data.instructions.length === 0 && <p className="muted">Пока нет опубликованных инструкций.</p>}
      <div className="grid">
        {data.instructions.map((item) => (
          <Link key={item.id} to={`/i/${item.id}`} className="card">
            <div className="card-title mb-8">{item.title}</div>
            <p className="muted mb-12">{item.summary}</p>
            <div className="card-meta">
              <span className="stars"><Icon name="star" size={14} /> {item.rating_avg}</span>
              <span>{item.steps_count} шагов</span>
              <span>{item.views} просмотров</span>
            </div>
          </Link>
        ))}
      </div>

      {error && <p className="error">{error}</p>}

      {editOpen && (
        <div className="modal-overlay active" onClick={(event) => { if (event.target === event.currentTarget) setEditOpen(false); }}>
          <div className="modal" ref={modalRef}>
            <button type="button" className="modal-close" onClick={() => setEditOpen(false)} aria-label="Закрыть">
              <Icon name="close" size={20} />
            </button>
            <h2>Редактирование профиля</h2>
            <p>Имя, описание и аватарка видны другим пользователям.</p>
            <div className="form-group" style={{ textAlign: "center" }}>
              {avatarUrl ? (
                <img src={assetUrl(avatarUrl)} alt="" className="avatar" style={{ objectFit: "cover", width: 64, height: 64, margin: "0 auto 12px" }} />
              ) : (
                <div className="avatar" style={{ margin: "0 auto 12px" }}>{name[0] || "?"}</div>
              )}
              <input type="file" accept="image/*" onChange={uploadAvatar} className="form-control" />
            </div>
            <div className="form-group">
              <label>Имя</label>
              <input className="form-control" value={name} onChange={(event) => setName(event.target.value)} />
            </div>
            <div className="form-group">
              <label>О себе</label>
              <textarea className="form-control" value={bio} onChange={(event) => setBio(event.target.value)} />
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-primary" onClick={save} disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</button>
              <button className="btn btn-outline" onClick={() => setEditOpen(false)}>Отмена</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
