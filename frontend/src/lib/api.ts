export const API = process.env.NEXT_PUBLIC_API || 'http://localhost:8080';

export async function fetchTrials(params: Record<string, any> = {}) {
  const qs = new URLSearchParams(params as any).toString();
  const res = await fetch(`${API}/api/trials?${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchTrial(id: string) {
  const res = await fetch(`${API}/api/trials/${encodeURIComponent(id)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function sendMail(body: any) {
  const res = await fetch(`${API}/api/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}