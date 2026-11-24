import { useState } from "react";
import { api, assetUrl } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../toast";
import AttachmentEditor from "./AttachmentEditor";

function formatDate(value) {
  if (!value) return "";
  return new Date(value).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
}

export default function Comments({
  instructionId,
  comments,
  steps = [],
  stepId = null,
  onRefresh,
  canResolve = false
}) {
  const { user, openAuth } = useAuth();
  const { ask, showToast } = useToast();
  const [body, setBody] = useState("");
  const [kind, setKind] = useState("comment");
  const [parentId, setParentId] = useState(null);
  const [suggestedBody, setSuggestedBody] = useState("");
  const [commentImages, setCommentImages] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const stepTitle = (id) => steps.find((step) => step.id === id)?.title;

  async function submit(event) {
    event.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    setError("");
    try {
      const created = await api(`/instructions/${instructionId}/comments`, {
        method: "POST",
        body: JSON.stringify({
          body: body.trim(),
          step_id: stepId,
          parent_id: parentId,
          kind,
          suggested_body: kind === "suggestion" ? suggestedBody.trim() : ""
        })
      });
      for (const image of commentImages) {
        await api("/attachments", {
          method: "POST",
          body: JSON.stringify({
            target_type: "comment",
            target_id: created.id,
            url: image.url || image
          })
        });
      }
      setBody("");
      setSuggestedBody("");
      setCommentImages([]);
      setParentId(null);
      await onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function resolve(id) {
    await api(`/comments/${id}/resolve`, { method: "POST" }).catch((err) => setError(err.message));
    await onRefresh();
  }

  async function accept(id) {
    try {
      await api(`/comments/${id}/accept`, { method: "POST" });
      await onRefresh();
      showToast("Предложение применено, создана новая версия");
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function remove(id) {
    if (!(await ask("Удалить комментарий?"))) return;
    await api(`/comments/${id}`, { method: "DELETE" }).catch((err) => setError(err.message));
    await onRefresh();
  }

  function renderComment(comment, depth = 0) {
    const replies = comments.filter((item) => item.parent_id === comment.id);
    const canDelete = user && (user.id === comment.user.id || canResolve);
    return (
      <div key={comment.id} style={{ marginLeft: depth * 24 }}>
        <div className="comment-item">
          <div className="comment-avatar">{comment.user.name[0]}</div>
          <div className="comment-body">
            <div className="comment-author">
              {comment.user.name} <span className="muted">{formatDate(comment.created_at)}</span>
              {comment.kind === "suggestion" && <span className="badge expert">Предложение</span>}
              {comment.resolved && <span className="badge">Решено</span>}
              {comment.accepted_at && <span className="badge">Принято</span>}
            </div>
            {comment.step_id && <div className="muted" style={{ fontSize: 13 }}>Шаг: {stepTitle(comment.step_id) || comment.step_id}</div>}
            <div>{comment.body}</div>
            {comment.suggested_body && <div className="muted mt-8">Предлагаемый текст: {comment.suggested_body}</div>}
            {comment.images?.length > 0 && (
              <div className="row gap-8 mt-8">
                {comment.images.map((image) => (
                  <img key={image.id} src={assetUrl(image.url)} alt="" style={{ width: 120, height: 90, objectFit: "cover", borderRadius: 8 }} />
                ))}
              </div>
            )}
            <div className="row gap-8 mt-8">
              {user && <button className="action-link" onClick={() => setParentId(comment.id)}>Ответить</button>}
              {canResolve && comment.kind === "suggestion" && comment.suggested_body && !comment.accepted_at && (
                <button className="btn btn-primary" onClick={() => accept(comment.id)}>Принять</button>
              )}
              {canResolve && <button className="action-link" onClick={() => resolve(comment.id)}>{comment.resolved ? "Вернуть" : "Решено"}</button>}
              {canDelete && <button className="action-link" onClick={() => remove(comment.id)}>Удалить</button>}
            </div>
          </div>
        </div>
        {replies.length > 0 && <div>{replies.map((reply) => renderComment(reply, depth + 1))}</div>}
      </div>
    );
  }

  const roots = comments.filter((comment) => !comment.parent_id);

  return (
    <section className="chart-box" id="comments">
      <h2 style={{ fontSize: 20 }}>Обсуждение</h2>
      {comments.length === 0 && <p className="muted mt-12">Пока пусто.</p>}
      <div className="comment-list mt-16">
        {roots.map((comment) => renderComment(comment))}
      </div>

      {user ? (
        <form onSubmit={submit}>
          {parentId && (
            <p className="muted mb-8">
              Ответ на комментарий #{parentId}{" "}
              <button type="button" className="action-link" onClick={() => setParentId(null)}>Отмена</button>
            </p>
          )}
          <textarea className="form-control" value={body} onChange={(event) => setBody(event.target.value)} placeholder="Комментарий или предложение" required />
          {kind === "suggestion" && (
            <textarea
              className="form-control mt-8"
              value={suggestedBody}
              onChange={(event) => setSuggestedBody(event.target.value)}
              placeholder="Как лучше переписать шаг"
            />
          )}
          <AttachmentEditor targetType="comment" targetId={null} attachments={commentImages} onChange={setCommentImages} label="Картинки к комментарию" />
          <div className="row gap-12 mt-12">
            <select className="form-control w-auto" value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="comment">Комментарий</option>
              <option value="suggestion">Предложение улучшения</option>
            </select>
            <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>{busy ? "Отправка..." : "Отправить"}</button>
          </div>
          {error && <p className="error">{error}</p>}
        </form>
      ) : (
        <p className="muted"><button type="button" className="action-link" onClick={() => openAuth("login")}>Войти</button>, чтобы оставить комментарий.</p>
      )}
    </section>
  );
}
