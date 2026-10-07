import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApiRead } from "../useApiRead.js";
import { ErrorBox, Loading } from "./Status.jsx";

const fetchUsers = (signal) => api.users({ signal });

export default function UserPicker({ value, onChange, label = "You are" }) {
  const { data: users, error, load } = useApiRead(fetchUsers);
  return (
    <div className="picker">
      <label htmlFor="user-picker">{label}</label>
      <select id="user-picker" disabled={!users} value={value ?? ""} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">Choose your name…</option>
        {(users ?? []).map((u) => (
          <option key={u.userId} value={u.userId}>{u.firstName} {u.lastName}</option>
        ))}
      </select>
      {!users && !error && <Loading what="Loading athletes" />}
      <ErrorBox error={error} onRetry={load} />
      <Link to="/join" className="link">Not listed? Join the challenge</Link>
    </div>
  );
}
