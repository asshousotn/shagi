import { useState } from "react";
import { api, assetUrl } from "../api";
import { useToast } from "../toast";
import Icon from "./Icon";

export default function AttachmentEditor({
  targetType,
  targetId,
  attachments = [],
  onChange,
  label = "Картинки"
}) {
  const { showToast } = useToast();
  const [busy, setBusy] = useState(false);

  async function add(event) {
    const files = Array.from(event.target.files || []);
    if (!files.length) return;
    setBusy(true);
    try {
      const uploaded = [];
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        const result = await api("/uploads", { method: "POST", body: form });
        uploaded.push(result.url);
      }
      if (targetId) {
        for (const url of uploaded) {
          await api("/attachments", {
            method: "POST",
            body: JSON.stringify({ target_type: targetType, target_id: targetId, url })
          });
        }
        onChange([...attachments, ...uploaded.map((url) => ({ url }))]);
      } else {
        onChange([...attachments, ...uploaded.map((url) => ({ url }))]);
      }
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  async function remove(item, index) {
    try {
      if (item.id) await api(`/attachments/${item.id}`, { method: "DELETE" });
      onChange(attachments.filter((_, current) => current !== index));
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  async function move(index, offset) {
    const next = index + offset;
    if (next < 0 || next >= attachments.length) return;
    try {
      if (attachments[index].id) {
        await api(`/attachments/${attachments[index].id}/position?position=${next}`, { method: "PATCH" });
      }
      const copy = [...attachments];
      [copy[index], copy[next]] = [copy[next], copy[index]];
      onChange(copy);
    } catch (err) {
      showToast(err.message, "error");
    }
  }

  return (
    <div className="form-group">
      <label>{label}</label>
      <input type="file" accept="image/*" multiple onChange={add} disabled={busy} className="form-control" />
      {busy && <p className="muted mt-8">Загружаем...</p>}
      {attachments.length > 0 && (
        <div className="row gap-8 mt-12">
          {attachments.map((item, index) => (
            <div key={item.id || `${item.url}-${index}`} style={{ position: "relative" }}>
              <img src={assetUrl(item.url || item)} alt="" style={{ width: 96, height: 72, objectFit: "cover", borderRadius: 8 }} />
              <button type="button" className="action-link" style={{ position: "absolute", top: 0, right: 0, background: "white", padding: "0 4px" }} onClick={() => remove(item, index)}>
                <Icon name="close" size={14} />
              </button>
              {(index > 0 || index < attachments.length - 1) && (
                <div className="row gap-8" style={{ marginTop: 2 }}>
                  {index > 0 && <button type="button" className="action-link" onClick={() => move(index, -1)}>←</button>}
                  {index < attachments.length - 1 && <button type="button" className="action-link" onClick={() => move(index, 1)}>→</button>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
