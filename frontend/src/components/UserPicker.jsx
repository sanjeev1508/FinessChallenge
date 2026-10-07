import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";

export default function UserPicker({ value, onChange, label = "You are" }) {
  const [users, setUsers] = useState([]);
  useEffect(() => { api.users().then(setUsers).catch(() => setUsers([])); }, []);
  return (
    <div className="picker">
      <label htmlFor="user-picker">{label}</label>
      <select id="user-picker" value={value ?? ""} onChange={(e) => onChange(e.target.value || null)}>
        <option value="">Choose your name…</option>
        {users.map((u) => (
          <option key={u.userId} value={u.userId}>{u.firstName} {u.lastName}</option>
        ))}
      </select>
      <Link to="/join" className="link">Not listed? Join the challenge</Link>
    </div>
  );
}
