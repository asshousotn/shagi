export default function CardSkeleton({ count = 6 }) {
  return (
    <div className="grid">
      {Array.from({ length: count }, (_, index) => (
        <div className="card" key={index}>
          <div className="skeleton" style={{ height: 22, width: "70%" }} />
          <div className="skeleton" style={{ height: 14, marginTop: 12 }} />
          <div className="skeleton" style={{ height: 14, width: "55%", marginTop: 8 }} />
          <div className="card-meta" style={{ marginTop: 16 }}>
            <div className="skeleton" style={{ height: 12, width: 60 }} />
            <div className="skeleton" style={{ height: 12, width: 60 }} />
          </div>
        </div>
      ))}
    </div>
  );
}
