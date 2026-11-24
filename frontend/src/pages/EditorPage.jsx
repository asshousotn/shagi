import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, assetUrl, uuid } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../toast";
import StepEditor from "../components/StepEditor";
import Icon from "../components/Icon";
import AttachmentEditor from "../components/AttachmentEditor";

export default function EditorPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { ask, showToast } = useToast();
  const navigate = useNavigate();
  const editing = Boolean(id);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [minutes, setMinutes] = useState(15);
  const [coverUrl, setCoverUrl] = useState("");
  const [tags, setTags] = useState("");
  const [steps, setSteps] = useState([]);
  const [categories, setCategories] = useState([]);
  const [importText, setImportText] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [preview, setPreview] = useState(false);
  const [instructionImages, setInstructionImages] = useState([]);

  useEffect(() => {
    api("/categories").then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    if (!id) {
      setTitle("");
      setSummary("");
      setCategoryId("");
      setDifficulty("medium");
      setMinutes(15);
      setCoverUrl("");
      setTags("");
      setSteps([]);
      setInstructionImages([]);
      return;
    }
    setError("");
    api(`/instructions/${id}`)
      .then((item) => {
        if (item.author.id !== user?.id) {
          setError("Это не ваша инструкция");
          return;
        }
        setTitle(item.title);
        setSummary(item.summary);
        setCategoryId(item.category?.id || "");
        setDifficulty(item.difficulty);
        setMinutes(item.minutes);
        setCoverUrl(item.cover_url);
        setTags(item.tags.map((tag) => tag.name).join(", "));
        setInstructionImages(item.images || []);
        setSteps(item.steps.map((step) => ({
          key: String(step.id), id: step.id, title: step.title, body: step.body, image_url: step.image_url, images: step.images || []
        })));
      })
      .catch((err) => setError(err.message));
  }, [id, user?.id]);

  function payload() {
    return {
      title: title.trim(),
      summary: summary.trim(),
      category_id: categoryId ? Number(categoryId) : null,
      difficulty,
      minutes: Number(minutes) || 15,
      cover_url: coverUrl.trim(),
      images: instructionImages.map((image) => image.url || image),
      tags: tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      steps: steps.map((step) => ({
        id: step.id,
        title: step.title,
        body: step.body,
        image_url: step.image_url,
        images: (step.images || []).map((image) => image.url || image)
      }))
    };
  }

  async function save(publish = false) {
    if (!title.trim()) {
      setError("Нужно название");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = editing
        ? await api(`/instructions/${id}`, { method: "PATCH", body: JSON.stringify(payload()) })
        : await api("/instructions", { method: "POST", body: JSON.stringify(payload()) });
      if (publish) await api(`/instructions/${saved.id}/publish`, { method: "POST" });
      if (!editing) {
        navigate(publish ? `/i/${saved.id}` : `/dashboard/${saved.id}/edit`);
        return;
      }
      setSteps(saved.steps.map((step) => ({
        key: String(step.id), id: step.id, title: step.title, body: step.body, image_url: step.image_url, images: step.images || []
      })));
      setInstructionImages(saved.images || []);
      setNotice(publish ? "Опубликовано" : "Сохранено");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!editing || !(await ask("Удалить инструкцию?"))) return;
    try {
      await api(`/instructions/${id}`, { method: "DELETE" });
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
    }
  }

  async function generate() {
    if (!title.trim() && !summary.trim()) {
      setError("Заполните название или описание");
      return;
    }
    setAiBusy(true);
    setError("");
    try {
      const result = await api("/ai/instruction", {
        method: "POST",
        body: JSON.stringify({ goal: `${title}. ${summary}`.trim() })
      });
      setTitle(result.title);
      setSummary(result.summary);
      setSteps(result.steps.map((step) => ({ key: uuid(), title: step.title, body: step.body, image_url: "" })));
      setNotice(result.ai ? "Черновик сгенерирован" : "ИИ не настроен, вставлен шаблон");
    } catch (err) {
      setError(err.message);
    } finally {
      setAiBusy(false);
    }
  }

  async function suggestTags() {
    if (!title.trim()) {
      setError("Сначала заполните название");
      return;
    }
    setAiBusy(true);
    try {
      const result = await api("/ai/tags", { method: "POST", body: JSON.stringify({ title, summary }) });
      setTags(result.tags.join(", "));
      setNotice(result.ai ? "Теги предложены" : "Теги собраны из названия");
    } catch (err) {
      setError(err.message);
    } finally {
      setAiBusy(false);
    }
  }

  async function uploadCover(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await api("/uploads", { method: "POST", body: form });
      setCoverUrl(result.url);
    } catch (err) {
      setError(err.message);
    }
  }

  function importSteps() {
    const lines = importText.split("\n").map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return;
    setSteps((current) => [
      ...current,
      ...lines.map((line) => ({ key: uuid(), title: line, body: "", image_url: "" }))
    ]);
    setImportText("");
  }

  return (
    <>
      <Link to="/dashboard" className="btn btn-outline mb-24">← Мои инструкции</Link>
      <div className="section-head">
        <h1>{editing ? "Редактирование" : "Новая инструкция"}</h1>
        <button className="btn btn-ai" onClick={generate} disabled={aiBusy}><Icon name="spark" size={16} /> Сгенерировать черновик</button>
      </div>
      {error && <p className="error">{error}</p>}
      {notice && <p className="muted">{notice}</p>}

      <div style={{ background: "white", padding: 32, borderRadius: "var(--radius)", boxShadow: "var(--shadow)", maxWidth: 800 }}>
        <div className="form-group">
          <label>Название инструкции</label>
          <input className="form-control" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Например: Как собрать ПК" />
        </div>
        <div className="form-group">
          <label>Краткое описание</label>
          <textarea className="form-control" value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="О чём эта инструкция" />
        </div>
        <div className="form-group">
          <label>Категория и сложность</label>
          <div className="row gap-12">
            <select className="form-control w-auto" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">Без категории</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
            <select className="form-control w-auto" value={difficulty} onChange={(event) => setDifficulty(event.target.value)}>
              <option value="easy">Легко</option>
              <option value="medium">Средне</option>
              <option value="hard">Сложно</option>
            </select>
            <input className="form-control" style={{ width: 100 }} type="number" min="1" value={minutes} onChange={(event) => setMinutes(event.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label>Обложка и теги</label>
          <input className="form-control" value={coverUrl} onChange={(event) => setCoverUrl(event.target.value)} placeholder="URL обложки" />
          <input className="form-control mt-12" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="Теги через запятую" />
          <input className="form-control mt-12" type="file" accept="image/*" onChange={uploadCover} />
          {coverUrl && <img src={assetUrl(coverUrl)} alt="" className="mt-12" style={{ maxWidth: 240, borderRadius: 10 }} />}
          <AttachmentEditor
            targetType="instruction"
            targetId={editing ? Number(id) : null}
            attachments={instructionImages}
            onChange={setInstructionImages}
            label="Галерея инструкции"
          />
        </div>
        <div className="row gap-12">
          <button className="btn btn-outline" onClick={suggestTags} disabled={aiBusy}>Подсказать теги</button>
          <button className="btn btn-outline" onClick={() => setPreview(!preview)}>{preview ? "Скрыть предпросмотр" : "Предпросмотр"}</button>
        </div>

        {preview && (
          <div className="chart-box mt-16">
            <h2>{title || "Новая инструкция"}</h2>
            <p className="muted mt-8">{summary}</p>
            <div className="mt-16">
              {steps.map((step, index) => (
                <div className="step-item" key={step.key}>
                  <div className="step-checkbox">{index + 1}</div>
                  <div className="step-content">
                    <h4>Шаг {index + 1}. {step.title}</h4>
                    <p className="muted">{step.body}</p>
                    {step.image_url && <img src={assetUrl(step.image_url)} alt="" className="mt-8" style={{ maxWidth: "100%" }} />}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <StepEditor steps={steps} setSteps={setSteps} />

        <div className="form-group mt-24">
          <label>Импорт шагов из текста</label>
          <textarea className="form-control" value={importText} onChange={(event) => setImportText(event.target.value)} placeholder="Каждая строка станет отдельным шагом" />
          <button className="btn btn-outline mt-12" onClick={importSteps}>Добавить строки как шаги</button>
        </div>

        <div style={{ display: "flex", gap: 12, marginTop: 24, flexWrap: "wrap" }}>
          <button className="btn btn-primary" onClick={() => save(false)} disabled={busy}>{busy ? "Сохранение..." : "Сохранить"}</button>
          <button className="btn btn-primary" onClick={() => save(true)} disabled={busy}>Опубликовать</button>
          {editing && <button className="btn btn-outline" onClick={remove}>Удалить</button>}
        </div>
      </div>
    </>
  );
}
