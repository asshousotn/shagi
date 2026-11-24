import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, assetUrl } from "../api";
import { useAuth } from "../auth";
import Icon from "../components/Icon";
import Skeleton from "../components/Skeleton";
import AttachmentEditor from "../components/AttachmentEditor";
import { useToast } from "../toast";

export default function ForumTopicPage() {
  const { id } = useParams();
  const { user, openAuth } = useAuth();
  const { showToast, ask } = useToast();
  const [topic, setTopic] = useState(null);
  const [body, setBody] = useState("");
  const [images, setImages] = useState([]);
  const [replyingTo, setReplyingTo] = useState(null);
  const [editId, setEditId] = useState(null);
  const [editBody, setEditBody] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      setTopic(await api(`/forum/topics/${id}`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => { load(); }, [id]);

  async function reply(event) {
    event.preventDefault();
    if (!user) return openAuth("login");
    try {
      await api(`/forum/topics/${id}/posts`, {
        method: "POST",
        body: JSON.stringify({
          body: body.trim(),
          parent_id: replyingTo,
          images: images.map((image) => image.url || image)
        })
      });
      setBody("");
      setImages([]);
      setReplyingTo(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function saveEdit(postId) {
    try {
      await api(`/forum/posts/${postId}`, {
        method: "PATCH",
        body: JSON.stringify({ body: editBody })
      });
      setEditId(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function solve(postId) {
    try {
      await api(`/forum/posts/${postId}/solution`, { method: "POST" });
      showToast("Отмечено как решение");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function react(postId) {
    try {
      await api("/reactions", {
        method: "POST",
        body: JSON.stringify({ target_type: "post", target_id: postId, value: 1 })
      });
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(postId) {
    if (!(await ask("Удалить сообщение?"))) return;
    try {
      await api(`/forum/posts/${postId}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function toggleClose() {
    try {
      await api(`/forum/topics/${id}/close`, { method: "POST" });
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (error && !topic) return <p className="error">{error}</p>;
  if (!topic) return <Skeleton lines={5} />;

  const canModerate = user && (user.role === "owner" || user.role === "admin" || user.id === topic.author.id);

  function renderPost(post, depth = 0) {
    const children = topic.posts.filter((item) => item.parent_id === post.id);
    const own = user?.id === post.author.id;
    return (
      <div key={post.id} style={{ marginLeft: depth * 24 }} className="mb-12">
        <div className={`card ${post.is_solution ? "bottleneck" : ""}`}>
          <div className="card-header">
            <div className="card-title">
              {post.is_solution && <span className="badge mr-8">Решение</span>}
              {post.author.name}
            </div>
            <span className="muted">
              {new Date(post.created_at).toLocaleString("ru-RU")}
              {post.updated_at && post.updated_at !== post.created_at && " · изменено"}
            </span>
          </div>
          {editId === post.id ? (
            <>
              <textarea className="form-control" value={editBody} onChange={(event) => setEditBody(event.target.value)} />
              <div className="row gap-12 mt-8">
                <button className="btn btn-primary btn-sm" onClick={() => saveEdit(post.id)}>Сохранить</button>
                <button className="action-link" onClick={() => setEditId(null)}>Отмена</button>
              </div>
            </>
          ) : (
            <p>{post.body}</p>
          )}
          {post.images.length > 0 && (
            <div className="row gap-8 mt-8">
              {post.images.map((image) => (
                <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 120, height: 90, objectFit: "cover", borderRadius: 8 }} />
              ))}
            </div>
          )}
          <div className="row gap-12 mt-8">
            <button type="button" className="action-link" onClick={() => react(post.id)}>Полезно</button>
            {!topic.closed && user && <button type="button" className="action-link" onClick={() => setReplyingTo(post.id)}>Ответить</button>}
            {canModerate && !post.is_solution && <button type="button" className="action-link" onClick={() => solve(post.id)}>Решение</button>}
            {own && <button type="button" className="action-link" onClick={() => { setEditId(post.id); setEditBody(post.body); }}>Изменить</button>}
            {(own || user?.role === "owner" || user?.role === "admin") && <button type="button" className="action-link" onClick={() => remove(post.id)}>Удалить</button>}
          </div>
        </div>
        {children.map((child) => renderPost(child, depth + 1))}
      </div>
    );
  }

  const roots = topic.posts.filter((post) => !post.parent_id);

  return (
    <>
      <Link to="/forum" className="btn btn-outline mb-24"><Icon name="left" size={16} /> К форуму</Link>
      <div className="section-head mb-24">
        <div>
          <h1>{topic.title}</h1>
          <p className="muted">
            {topic.author.name} · {new Date(topic.created_at).toLocaleString("ru-RU")} · {topic.views} просмотров
            {topic.solved_at && <span className="badge ml-8">Решено</span>}
            {topic.instruction_id && <> · <Link to={`/i/${topic.instruction_id}`}>инструкция #{topic.instruction_id}</Link></>}
          </p>
        </div>
        {canModerate && <button className="btn btn-outline" onClick={toggleClose}>{topic.closed ? "Открыть" : "Закрыть"}</button>}
      </div>

      <div className="chart-box mb-24">
        <p>{topic.body}</p>
        {topic.images.length > 0 && (
          <div className="row gap-8 mt-12">
            {topic.images.map((image) => (
              <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 160, height: 110, objectFit: "cover", borderRadius: 8 }} />
            ))}
          </div>
        )}
      </div>

      <h2 className="mb-16">Ответы ({topic.posts.length})</h2>
      {roots.length === 0 && <p className="muted">Ответов пока нет.</p>}
      {roots.map((post) => renderPost(post))}

      {error && <p className="error mt-16">{error}</p>}

      <form className="chart-box mt-24" onSubmit={reply}>
        <h3 className="mb-16">{replyingTo ? "Ответ на сообщение" : "Ответить"}</h3>
        {replyingTo && <button type="button" className="action-link mb-8" onClick={() => setReplyingTo(null)}>Отменить ответ</button>}
        {topic.closed ? (
          <p className="muted">Тема закрыта.</p>
        ) : user ? (
          <>
            <textarea className="form-control" value={body} onChange={(event) => setBody(event.target.value)} required />
            <AttachmentEditor targetType="post" targetId={null} attachments={images} onChange={setImages} label="Картинки к ответу" />
            <button className="btn btn-primary mt-12" type="submit">Отправить</button>
          </>
        ) : (
          <p><button type="button" className="btn btn-outline" onClick={() => openAuth("login")}>Войти</button>, чтобы ответить.</p>
        )}
      </form>
    </>
  );
}
