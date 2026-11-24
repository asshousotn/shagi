import { useEffect } from "react";

export function useModalFocus(active, ref, onClose) {
  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    const first = node?.querySelector("input, textarea, select, button, a[href]");
    first?.focus();

    function onKey(event) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !node) return;
      const items = [
        ...node.querySelectorAll("button, input, textarea, select, a[href]")
      ].filter((element) => !element.disabled);
      if (!items.length) return;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey && document.activeElement === firstItem) {
        event.preventDefault();
        lastItem.focus();
      } else if (!event.shiftKey && document.activeElement === lastItem) {
        event.preventDefault();
        firstItem.focus();
      }
    }

    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [active, ref, onClose]);
}
