export function Loading({ what = "Loading" }) {
  return <p className="status" role="status">{what}…</p>;
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-box" role="alert">
      <p>{error.message}</p>
      {error.details?.length > 0 && (
        <ul>{error.details.map((d, i) => <li key={i}><b>{d.field}</b>: {d.message}</li>)}</ul>
      )}
      {onRetry && <button className="btn ghost" onClick={onRetry}>Try again</button>}
    </div>
  );
}
