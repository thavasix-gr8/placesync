export default function Skeleton({ count = 3 }) {
  return <div className="skeleton-list">{Array.from({ length: count }, (_, index) => <div className="skeleton" key={index} />)}</div>
}
