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

  // 본문을 먼저 텍스트로 읽고, 가능하면 JSON 파싱
  const text = await res.text();
  let data: any = null;
  try { data = JSON.parse(text); } catch {}

  if (!res.ok) {
    // 백엔드가 내려준 상세 에러를 우선 노출
    const detail = data?.error || text || `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data ?? {};
}