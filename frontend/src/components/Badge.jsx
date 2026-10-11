import { statusClass } from '../utils/formatters'

export default function Badge({ children, status }) {
  return <span className={`badge ${statusClass(status || children)}`}>{children}</span>
}
