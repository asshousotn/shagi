import { useState } from "react";
import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, assetUrl, uuid } from "../api";
import { useToast } from "../toast";
import AttachmentEditor from "./AttachmentEditor";

function SortableStep({ step, index, onChange, onRemove }) {
  const { showToast } = useToast();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: step.key });
  const [busy, setBusy] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1
  };

  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    const data = new FormData();
    data.append("file", file);
    try {
      const result = await api("/uploads", { method: "POST", body: data });
      onChange({ image_url: result.url });
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function improve() {
    if (!step.body && !step.title) return;
    setBusy(true);
    try {
      const result = await api("/ai/improve", {
        method: "POST",
        body: JSON.stringify({ text: step.body || step.title })
      });
      onChange({ body: result.text });
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div ref={setNodeRef} style={style} className="step-row">
      <button
        type="button"
        className="drag"
        {...attributes}
        {...listeners}
        title="Перетащить"
      >
        ⋮⋮
      </button>
      <div style={{ flex: 1 }}>
        <div className="muted">Шаг {index + 1}</div>
        <input className="form-control"
          value={step.title}
          onChange={(event) => onChange({ title: event.target.value })}
          placeholder="Название шага"
          required
        />
        <textarea className="form-control"
          value={step.body}
          onChange={(event) => onChange({ body: event.target.value })}
          placeholder="Что сделать"
        />
        <input className="form-control"
          value={step.image_url}
          onChange={(event) => onChange({ image_url: event.target.value })}
          placeholder="URL картинки"
        />
        {step.image_url && (
          <img src={assetUrl(step.image_url)} alt="" style={{ maxWidth: 220 }} className="mt-8" />
        )}
        <AttachmentEditor
          targetType="step"
          targetId={step.id || null}
          attachments={step.images || []}
          onChange={(next) => onChange({ images: next })}
          label="Фото шага"
        />
        <button type="button" className="btn btn-ai" onClick={improve} disabled={busy}>
          Улучшить ИИ
        </button>
        <button type="button" className="btn btn-outline" onClick={onRemove}>
          Удалить шаг
        </button>
      </div>
    </div>
  );
}

export default function StepEditor({ steps, setSteps }) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  function update(key, patch) {
    setSteps((current) =>
      current.map((step) => (step.key === key ? { ...step, ...patch } : step))
    );
  }

  function remove(key) {
    setSteps((current) => current.filter((step) => step.key !== key));
  }

  function add() {
    setSteps((current) => [
      ...current,
      { key: uuid(), title: "", body: "", image_url: "", images: [] }
    ]);
  }

  function dragEnd({ active, over }) {
    if (!over || active.id === over.id) return;
    const oldIndex = steps.findIndex((step) => step.key === active.id);
    const newIndex = steps.findIndex((step) => step.key === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    setSteps(arrayMove(steps, oldIndex, newIndex));
  }

  return (
    <div>
      <h2>Шаги</h2>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={dragEnd}>
        <SortableContext items={steps.map((step) => step.key)} strategy={verticalListSortingStrategy}>
          {steps.map((step, index) => (
            <SortableStep
              key={step.key}
              step={step}
              index={index}
              onChange={(patch) => update(step.key, patch)}
              onRemove={() => remove(step.key)}
            />
          ))}
        </SortableContext>
      </DndContext>
      <button type="button" className="btn btn-outline" onClick={add}>
        Добавить шаг
      </button>
    </div>
  );
}
