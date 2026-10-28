import { useEffect, useState } from "react";
import App from "./App.jsx";
import "./AuthGate.css";

const TOKEN_KEY = "smart_xray_access_token";
const USER_KEY = "smart_xray_user";

async function apiFetch(path, token, options = {}) {
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(path, {
    ...options,
    headers,
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!username.trim() || !password) {
      setError("Please enter a username and password.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      onLogin(data);
    } catch (err) {
      setError(err.message || "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand-panel">
        <div className="auth-brand-content">
          <div className="auth-logo">🩻</div>
          <h1>Smart X-Ray AI</h1>
          <p>Secure AI-Assisted Chest X-Ray Analysis</p>

          <div className="auth-security-note">
            <strong>Protected access</strong>
            <span>
              Authorized users only. Activity is recorded in the system Audit Trail.
            </span>
          </div>
        </div>
      </div>

      <div className="auth-form-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-heading">
            <h2>Sign in</h2>
            <p>Enter your Smart X-Ray AI account credentials.</p>
          </div>

          <label className="login-field">
            <span>Username</span>
            <input
              type="text"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="Enter username"
            />
          </label>

          <label className="login-field">
            <span>Password</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter password"
            />
          </label>

          {error && <div className="login-error">{error}</div>}

          <button
            className="login-button"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>

          <p className="login-disclaimer">
            Educational decision-support prototype. This system does not provide
            a medical diagnosis.
          </p>
        </form>
      </div>
    </div>
  );
}

function RecordsPanel({ token }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRecords = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await apiFetch("/records?limit=200", token);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not load records.");
      }

      setRecords(data.records || []);
    } catch (err) {
      setError(err.message || "Could not load records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const exportRecord = async (recordId) => {
    setError("");

    try {
      const response = await apiFetch(
        `/records/${encodeURIComponent(recordId)}/export`,
        token
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Could not export record.");
      }

      const blob = await response.blob();
      downloadBlob(blob, `analysis_record_${recordId}.json`);
    } catch (err) {
      setError(err.message || "Could not export record.");
    }
  };

  return (
    <main className="secure-main">
      <section className="secure-card">
        <div className="panel-heading">
          <div>
            <h2>Analysis Records</h2>
            <p>
              Stored analysis metadata and AI results. Uploaded image bytes are
              not stored in this records database.
            </p>
          </div>
          <button className="secondary-button" onClick={loadRecords}>
            Refresh
          </button>
        </div>

        {error && <div className="secure-error">{error}</div>}

        {loading ? (
          <div className="empty-state">Loading records...</div>
        ) : records.length === 0 ? (
          <div className="empty-state">No analysis records are available yet.</div>
        ) : (
          <div className="table-scroll">
            <table className="secure-table">
              <thead>
                <tr>
                  <th>Date / Time</th>
                  <th>User</th>
                  <th>Role</th>
                  <th>Detected findings</th>
                  <th>Scores</th>
                  <th>Record</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td>{record.created_at}</td>
                    <td>{record.username}</td>
                    <td>
                      <span className="role-badge">{record.role}</span>
                    </td>
                    <td>
                      {record.detected_findings?.length
                        ? record.detected_findings.join(", ")
                        : "No selected finding detected"}
                    </td>
                    <td>
                      <div className="score-list">
                        {Object.entries(record.scores || {}).length ? (
                          Object.entries(record.scores || {}).map(
                            ([finding, score]) => (
                              <span key={finding}>
                                {finding}: {(Number(score) * 100).toFixed(2)}%
                              </span>
                            )
                          )
                        ) : (
                          <span>Not available</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <div className="record-actions">
                        <code>{record.id.slice(0, 8)}…</code>
                        <button
                          className="table-button"
                          onClick={() => exportRecord(record.id)}
                        >
                          Export JSON
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function AdminPanel({ token, currentUser }) {
  const [users, setUsers] = useState([]);
  const [events, setEvents] = useState([]);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("DOCTOR");
  const [creating, setCreating] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    setError("");

    try {
      const [usersResponse, auditResponse] = await Promise.all([
        apiFetch("/admin/users", token),
        apiFetch("/audit?limit=100", token),
      ]);

      const usersData = await usersResponse.json();
      const auditData = await auditResponse.json();

      if (!usersResponse.ok) {
        throw new Error(usersData.detail || "Could not load users.");
      }

      if (!auditResponse.ok) {
        throw new Error(auditData.detail || "Could not load Audit Trail.");
      }

      setUsers(usersData.users || []);
      setEvents(auditData.events || []);
    } catch (err) {
      setError(err.message || "Could not load administration data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const verifyAudit = async () => {
    setError("");
    setMessage("");

    try {
      const response = await apiFetch("/audit/verify", token);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not verify Audit Trail.");
      }

      setVerification(data);
      setMessage(data.message || "Audit verification completed.");
      await loadAdminData();
    } catch (err) {
      setError(err.message || "Could not verify Audit Trail.");
    }
  };

  const exportAudit = async () => {
    setError("");

    try {
      const response = await apiFetch("/audit/export", token);

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Could not export Audit Trail.");
      }

      const blob = await response.blob();
      downloadBlob(blob, "smart_xray_audit.csv");
      setMessage("Audit Trail exported successfully.");
      await loadAdminData();
    } catch (err) {
      setError(err.message || "Could not export Audit Trail.");
    }
  };

  const createUser = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!newUsername.trim() || !newPassword) {
      setError("Username and password are required.");
      return;
    }

    setCreating(true);

    try {
      const response = await apiFetch("/admin/users", token, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: newUsername.trim(),
          password: newPassword,
          role: newRole,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not create user.");
      }

      setNewUsername("");
      setNewPassword("");
      setNewRole("DOCTOR");
      setMessage(`User "${data.user.username}" created successfully.`);
      await loadAdminData();
    } catch (err) {
      setError(err.message || "Could not create user.");
    } finally {
      setCreating(false);
    }
  };

  const changeUserStatus = async (user) => {
    setError("");
    setMessage("");

    const nextActive = !Boolean(user.active);

    try {
      const response = await apiFetch(
        `/admin/users/${user.id}/active`,
        token,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ active: nextActive }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Could not change account status.");
      }

      setMessage(
        `Account "${data.user.username}" is now ${
          data.user.active ? "active" : "inactive"
        }.`
      );
      await loadAdminData();
    } catch (err) {
      setError(err.message || "Could not change account status.");
    }
  };

  return (
    <main className="secure-main">
      <section className="secure-card">
        <div className="panel-heading">
          <div>
            <h2>User Administration</h2>
            <p>
              Create accounts and control active access. Roles are ADMIN,
              DOCTOR and TECHNICIAN.
            </p>
          </div>
          <button className="secondary-button" onClick={loadAdminData}>
            Refresh
          </button>
        </div>

        {error && <div className="secure-error">{error}</div>}
        {message && <div className="secure-success">{message}</div>}

        <form className="create-user-form" onSubmit={createUser}>
          <label>
            <span>Username</span>
            <input
              value={newUsername}
              onChange={(event) => setNewUsername(event.target.value)}
              placeholder="New username"
            />
          </label>

          <label>
            <span>Temporary password</span>
            <input
              type="password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              placeholder="Temporary password"
            />
          </label>

          <label>
            <span>Role</span>
            <select
              value={newRole}
              onChange={(event) => setNewRole(event.target.value)}
            >
              <option value="ADMIN">ADMIN</option>
              <option value="DOCTOR">DOCTOR</option>
              <option value="TECHNICIAN">TECHNICIAN</option>
            </select>
          </label>

          <button className="primary-small-button" disabled={creating}>
            {creating ? "Creating..." : "Create user"}
          </button>
        </form>

        {loading ? (
          <div className="empty-state">Loading users...</div>
        ) : (
          <div className="table-scroll">
            <table className="secure-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Access</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const isCurrentUser = Number(user.id) === Number(currentUser.id);

                  return (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>
                        <span className="role-badge">{user.role}</span>
                      </td>
                      <td>
                        <span
                          className={
                            user.active ? "status-active" : "status-inactive"
                          }
                        >
                          {user.active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td>{user.created_at}</td>
                      <td>
                        <button
                          className="table-button"
                          disabled={isCurrentUser && Boolean(user.active)}
                          onClick={() => changeUserStatus(user)}
                        >
                          {user.active ? "Deactivate" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="secure-card">
        <div className="panel-heading">
          <div>
            <h2>Audit Trail</h2>
            <p>
              Time-stamped security and application events with a SHA-256 hash
              chain for integrity verification.
            </p>
          </div>

          <div className="panel-actions">
            <button className="secondary-button" onClick={verifyAudit}>
              Verify chain
            </button>
            <button className="secondary-button" onClick={exportAudit}>
              Export CSV
            </button>
          </div>
        </div>

        {verification && (
          <div
            className={
              verification.valid
                ? "audit-verification valid"
                : "audit-verification invalid"
            }
          >
            {verification.valid ? "✓" : "!"} {verification.message}
          </div>
        )}

        {loading ? (
          <div className="empty-state">Loading Audit Trail...</div>
        ) : events.length === 0 ? (
          <div className="empty-state">No audit events are available.</div>
        ) : (
          <div className="table-scroll">
            <table className="secure-table audit-table">
              <thead>
                <tr>
                  <th>Date / Time</th>
                  <th>User</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id}>
                    <td>{event.created_at}</td>
                    <td>{event.username}</td>
                    <td>{event.role}</td>
                    <td>
                      <code>{event.action}</code>
                    </td>
                    <td>{event.status}</td>
                    <td>{event.details}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

export default function AuthGate() {
  const [token, setToken] = useState(() =>
    sessionStorage.getItem(TOKEN_KEY)
  );
  const [user, setUser] = useState(() => {
    const stored = sessionStorage.getItem(USER_KEY);

    if (!stored) {
      return null;
    }

    try {
      return JSON.parse(stored);
    } catch {
      return null;
    }
  });

  const [checkingSession, setCheckingSession] = useState(Boolean(token));
  const [activeSection, setActiveSection] = useState("analysis");

  useEffect(() => {
    let cancelled = false;

    const validateSession = async () => {
      if (!token) {
        setCheckingSession(false);
        return;
      }

      try {
        const response = await apiFetch("/auth/me", token);

        if (!response.ok) {
          throw new Error("Session expired.");
        }

        const currentUser = await response.json();

        if (!cancelled) {
          setUser(currentUser);
          sessionStorage.setItem(USER_KEY, JSON.stringify(currentUser));
        }
      } catch {
        if (!cancelled) {
          sessionStorage.removeItem(TOKEN_KEY);
          sessionStorage.removeItem(USER_KEY);
          setToken(null);
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setCheckingSession(false);
        }
      }
    };

    validateSession();

    return () => {
      cancelled = true;
    };
  }, [token]);

  /*
   * App.jsx already uses fetch("/predict") and fetch("/gradcam").
   * This wrapper adds the Bearer token to same-origin API requests so the
   * existing X-ray interface can remain unchanged.
   */
  useEffect(() => {
    if (!token) {
      return undefined;
    }

    const previousFetch = window.fetch.bind(window);

    const authenticatedFetch = (input, options = {}) => {
      const requestUrl =
        typeof input === "string"
          ? input
          : input instanceof Request
          ? input.url
          : "";

      let sameOrigin = false;

      try {
        const resolved = new URL(requestUrl, window.location.origin);
        sameOrigin = resolved.origin === window.location.origin;
      } catch {
        sameOrigin = requestUrl.startsWith("/");
      }

      if (!sameOrigin || requestUrl.includes("/auth/login")) {
        return previousFetch(input, options);
      }

      const existingHeaders =
        options.headers ||
        (input instanceof Request ? input.headers : undefined);

      const headers = new Headers(existingHeaders || {});
      headers.set("Authorization", `Bearer ${token}`);

      return previousFetch(input, {
        ...options,
        headers,
      });
    };

    window.fetch = authenticatedFetch;

    return () => {
      window.fetch = previousFetch;
    };
  }, [token]);

  const handleLogin = (data) => {
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));
    setToken(data.access_token);
    setUser(data.user);
    setActiveSection("analysis");
  };

  const handleLogout = async () => {
    try {
      if (token) {
        await apiFetch("/auth/logout", token, {
          method: "POST",
        });
      }
    } catch {
      // The local session is still cleared if the server is unavailable.
    } finally {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(USER_KEY);
      setToken(null);
      setUser(null);
      setActiveSection("analysis");
    }
  };

  if (checkingSession) {
    return (
      <div className="session-check">
        <div className="session-spinner" />
        <p>Checking secure session...</p>
      </div>
    );
  }

  if (!token || !user) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  const canViewRecords = user.role === "ADMIN" || user.role === "DOCTOR";
  const isAdmin = user.role === "ADMIN";

  return (
    <div className="secure-shell">
      <div className="secure-topbar">
        <div className="secure-topbar-brand">
          <span className="secure-topbar-icon">🩻</span>
          <div>
            <strong>Smart X-Ray AI</strong>
            <span>Secure workspace</span>
          </div>
        </div>

        <nav className="secure-nav" aria-label="Application sections">
          <button
            className={activeSection === "analysis" ? "active" : ""}
            onClick={() => setActiveSection("analysis")}
          >
            Analysis
          </button>

          {canViewRecords && (
            <button
              className={activeSection === "records" ? "active" : ""}
              onClick={() => setActiveSection("records")}
            >
              Records
            </button>
          )}

          {isAdmin && (
            <button
              className={activeSection === "admin" ? "active" : ""}
              onClick={() => setActiveSection("admin")}
            >
              Administration
            </button>
          )}
        </nav>

        <div className="secure-user-area">
          <div className="secure-user-text">
            <strong>{user.username}</strong>
            <span>{user.role}</span>
          </div>
          <button className="logout-button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </div>

      {activeSection === "analysis" && <App />}

      {activeSection === "records" && canViewRecords && (
        <RecordsPanel token={token} />
      )}

      {activeSection === "admin" && isAdmin && (
        <AdminPanel token={token} currentUser={user} />
      )}
    </div>
  );
}
