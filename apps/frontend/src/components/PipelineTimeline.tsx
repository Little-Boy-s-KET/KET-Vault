/**
 * KET Board - Pipeline Timeline Component.
 *
 * Vertical timeline showing each step of the consensus process.
 * Updated to match usePipeline hook's TimelineEntry format.
 */

interface TimelineEntry {
  time: string;
  message: string;
  type: "info" | "agent" | "consensus" | "error";
}

interface Props {
  entries: TimelineEntry[];
}

export function PipelineTimeline({ entries }: Props) {
  if (entries.length === 0) return null;

  const statusMap: Record<TimelineEntry["type"], string> = {
    info: "completed",
    agent: "active",
    consensus: "completed",
    error: "rejected",
  };

  return (
    <div className="timeline">
      <h3 className="timeline-title">Pipeline Timeline</h3>
      <div className="timeline-items">
        {entries.map((entry, i) => (
          <div
            key={`${entry.time}-${i}`}
            className={`timeline-item ${statusMap[entry.type]}`}
            style={{ animationDelay: `${i * 0.1}s` }}
          >
            <span className="timeline-time">{entry.time}</span>
            <span className="timeline-text">{entry.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
