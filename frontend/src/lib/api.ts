export const API = process.env.NEXT_PUBLIC_API || 'http://localhost:8080';

export async function fetchTrials(params: Record<string, any> = {}) {
  const { sheet, ...rest } = params;
  const endpoint = sheet === 'N' ? 'n' : 'y'; // 기본 y
  const qs = new URLSearchParams(rest as any).toString();
  const url = `${API}/api/trials/${endpoint}${qs ? `?${qs}` : ''}`;

  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchTrial(id: string) {
  // ✅ 반드시 encodeURIComponent 처리
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

  const text = await res.text();
  let data: any = null;
  try { data = JSON.parse(text); } catch {}

  if (!res.ok) {
    const detail = data?.error || text || `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data ?? {};
}