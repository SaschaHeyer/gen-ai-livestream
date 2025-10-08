"use client";

import { FormEvent, useEffect, useState } from "react";

type UploadLog = {
  timestamp: string;
  fileName: string;
  note: string;
};

const LOGIN_CREDENTIALS = {
  username: "test",
  password: "test",
};

export default function HomePage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [logs, setLogs] = useState<UploadLog[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchLogs = async () => {
    try {
      const response = await fetch("/api/upload", { cache: "no-store" });
      if (!response.ok) {
        throw new Error("Failed to load logs");
      }
      const payload = await response.json();
      setLogs(payload.logs ?? []);
    } catch (error) {
      console.error(error);
    }
  };

  useEffect(() => {
    fetchLogs().catch(console.error);
  }, []);

  const handleLogin = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (
      username.trim() === LOGIN_CREDENTIALS.username &&
      password.trim() === LOGIN_CREDENTIALS.password
    ) {
      setIsAuthenticated(true);
      setMessage(null);
    } else {
      setMessage("Invalid credentials. Try test / test.");
    }
  };

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setMessage("Please choose a PDF before uploading.");
      return;
    }
    setIsSubmitting(true);
    setMessage("Uploading...");
    try {
      const formData = new FormData();
      formData.append("note", note);
      formData.append("file", file);
      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }
      const payload = await response.json();
      setMessage(`Uploaded ${payload.entry.fileName} successfully.`);
      setNote("");
      setFile(null);
      await fetchLogs();
    } catch (error: any) {
      setMessage(error?.message ?? "Upload failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="container">
      <section className="card">
        <h1>Automation Portal</h1>
        {!isAuthenticated ? (
          <form onSubmit={handleLogin} className="form">
            <label>
              Username
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="Enter username"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter password"
                required
              />
            </label>
            <button type="submit">Log in</button>
          </form>
        ) : (
          <form onSubmit={handleUpload} className="form">
            <label>
              Notes
              <textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Type something to attach with your upload"
                rows={4}
              />
            </label>
            <label>
              Upload PDF
              <input
                type="file"
                accept="application/pdf"
                onChange={(event) => {
                  const selected = event.target.files?.[0];
                  setFile(selected ?? null);
                }}
                required
              />
            </label>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Uploading..." : "Upload File"}
            </button>
          </form>
        )}
        {message && <p className="message">{message}</p>}
      </section>

      <section className="card logs">
        <h2>Upload Activity</h2>
        {logs.length === 0 ? (
          <p className="empty">No uploads recorded yet.</p>
        ) : (
          <ul>
            {logs.map((log) => (
              <li key={`${log.timestamp}-${log.fileName}`}>
                <span className="log-time">
                  {new Date(log.timestamp).toLocaleString()}
                </span>
                <span className="log-file">{log.fileName}</span>
                {log.note && <span className="log-note">“{log.note}”</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
