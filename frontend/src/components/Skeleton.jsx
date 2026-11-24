export default function Skeleton({ lines = 3 }) {
  return (
    <div style={{ maxWidth: 480 }}>
      {Array.from({ length: lines }, (_, index) => (
        <div key={index} className="skeleton" style={{ width: `${100 - index * 12}%` }} />
      ))}
    </div>
  );
}
