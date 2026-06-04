import { Icon } from "@/components/Icon";

export function LoadingBubble() {
  return (
    <div className="mf-msg-row">
      <div className="mf-avatar">
        <Icon name="smart_toy" size={20} />
      </div>
      <div className="mf-msg-bubble">
        <div className="mf-typing" aria-label="Loading">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}
