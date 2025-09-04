// src/pages/trials/[id].tsx
import { useRouter } from "next/router";
import { useEffect, useMemo, useState } from "react";

import {
  Box,
  Heading,
  Text,
  HStack,
  VStack,
  Button,
  Badge,
  Separator,
  Table,
  Code,
  Field,
  Input,
  Select,
  createListCollection,
  Spinner,
} from "@chakra-ui/react";

import { toaster } from "@/components/ui/toaster";

// --- API helpers -------------------------------------------------
const API = "http://localhost:8080";

async function fetchJSON<T>(url: string) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return (await r.json()) as T;
}

async function getTrial(id: string) {
  // id에 한글/특수문자 포함되므로 인코딩
  return await fetchJSON<any>(`${API}/api/trials/${encodeURIComponent(id)}`);
}

async function fetchTemplates() {
  return await fetchJSON<Array<{ id: string; label: string; default_subject: string }>>(
    `${API}/api/templates`
  );
}

async function sendMail(payload: {
  id: string;
  template: string;
  subject?: string;
  context?: Record<string, any>;
}) {
  const r = await fetch(`${API}/api/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data?.error || `HTTP ${r.status}`);
  return data;
}

// --- 컴포넌트 -----------------------------------------------------
const TEMPLATE_COLLECTION = createListCollection({
  items: [] as { label: string; value: string; meta: { id: string; label: string; default_subject: string } }[],
});

export default function TrialDetailPage() {
  const router = useRouter();
  const { id } = router.query;

  const [loading, setLoading] = useState(true);
  const [item, setItem] = useState<any | null>(null);
  const [sending, setSending] = useState(false);

  // 템플릿 선택/제목/컨텍스트
  const [templates, setTemplates] = useState<Array<{ id: string; label: string; default_subject: string }>>([]);
  const [selectedTpl, setSelectedTpl] = useState<string>("");
  const [subject, setSubject] = useState<string>("");

  // 컨텍스트: 템플릿은 내부에 고정 URL/이미지 사용 → 필요한 건 수신자 표시명만
  const [ctx, setCtx] = useState({
    recipient_name: "",
  });

  // 상세 로드
  useEffect(() => {
    (async () => {
      if (!id || typeof id !== "string") return;
      try {
        const data = await getTrial(id);
        setItem(data);
      } catch (e: any) {
        toaster.create({ title: "상세 조회 실패", description: String(e?.message || e), type: "error" });
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  // 템플릿 로드
  useEffect(() => {
    (async () => {
      try {
        const list = await fetchTemplates();
        setTemplates(list);
        TEMPLATE_COLLECTION.items = list.map((t) => ({
          label: t.label,
          value: t.id,
          meta: t,
        }));
        if (list.length && !selectedTpl) {
          setSelectedTpl(list[0].id);
          setSubject(list[0].default_subject);
        }
      } catch (e: any) {
        toaster.create({ title: "템플릿 목록 로드 실패", description: String(e?.message || e), type: "error" });
      }
    })();
  }, []);

  // 템플릿 바뀌면 subject 기본값 갱신
  function onChangeTemplate(newId: string) {
    setSelectedTpl(newId);
    const meta = templates.find((t) => t.id === newId);
    if (meta) setSubject(meta.default_subject);
  }

  const title = useMemo(() => {
    if (!item) return "";
    const company = item["회사명"] || item["company"] || "";
    const manager = item["담당자"] || item["manager"] || "";
    return company ? `${company} (${manager || "-"})` : item._id;
  }, [item]);

  const isMeta = !!item?._meta; // 백엔드가 noise/meta 행에 _meta 세팅

  async function onSend() {
    if (!item) return;
    if (!selectedTpl) {
      toaster.create({ title: "템플릿을 선택해 주세요", type: "warning" });
      return;
    }
    try {
      setSending(true);
      await sendMail({
        id: item._id, // "트라이얼(Y):12" 형식
        template: selectedTpl,
        subject,
        context: ctx, // recipient_name만 전달
      });
      toaster.create({ title: "메일 전송 완료", description: subject, type: "success" });
    } catch (e: any) {
      toaster.create({ title: "메일 전송 실패", description: String(e?.message || e), type: "error" });
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <VStack p={6} gap={4} align="center" justify="center">
        <Spinner />
        <Text>불러오는 중...</Text>
      </VStack>
    );
  }

  if (!item) {
    return (
      <VStack p={6} gap={4} align="start">
        <Heading size="md">데이터가 없습니다.</Heading>
        <Button variant="outline" onClick={() => router.push("/trials")}>
          목록으로
        </Button>
      </VStack>
    );
  }

  return (
    <VStack align="stretch" gap={6} p={6}>
      {/* 헤더 */}
      <HStack justify="space-between" wrap="wrap" gap={3}>
        <HStack gap={3} align="center">
          <Heading size="lg">{title}</Heading>
          {isMeta && <Badge colorPalette="yellow">메타(요약/구분) 행</Badge>}
        </HStack>
        <HStack gap={2}>
          <Button variant="outline" onClick={() => router.back()}>
            뒤로
          </Button>
          <Button colorScheme="blue" onClick={onSend} loading={sending} disabled={isMeta}>
            메일 보내기
          </Button>
        </HStack>
      </HStack>

      {/* 메일 템플릿/제목/컨텍스트 입력 */}
      <Box border="1px solid" borderColor="gray.200" rounded="lg" p={4}>
        <Heading size="sm" mb={3}>
          메일 템플릿
        </Heading>

        <HStack gap={3} wrap="wrap" mb={3}>
          {/* 템플릿 선택 */}
          <Field.Root>
            <Field.Label>템플릿</Field.Label>
            <Select.Root
              collection={TEMPLATE_COLLECTION}
              value={selectedTpl ? [selectedTpl] : []}
              onValueChange={(e) => onChangeTemplate(e.value[0] ?? "")}
              size="sm"
              width="360px"
            >
              <Select.Control>
                <Select.Trigger>
                  <Select.ValueText placeholder="템플릿 선택" />
                </Select.Trigger>
              </Select.Control>
              <Select.Positioner>
                <Select.Content>
                  {TEMPLATE_COLLECTION.items.map((opt) => (
                    <Select.Item key={opt.value} item={opt}>
                      {opt.label}
                    </Select.Item>
                  ))}
                </Select.Content>
              </Select.Positioner>
            </Select.Root>
          </Field.Root>

          {/* 메일 제목 */}
          <Field.Root>
            <Field.Label>제목</Field.Label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              width="420px"
              placeholder="메일 제목"
              size="sm"
            />
          </Field.Root>
        </HStack>

        {/* 컨텍스트 입력: recipient_name만 */}
        <VStack align="stretch" gap={3}>
          <Field.Root>
            <Field.Label>수신자 표시명 (recipient_name)</Field.Label>
            <Input
              size="sm"
              value={ctx.recipient_name}
              onChange={(e) => setCtx({ ...ctx, recipient_name: e.target.value })}
              placeholder="예: 임재언 고객님"
            />
          </Field.Root>
        </VStack>
      </Box>

      <Separator />

      {/* 기본 정보 */}
      <Section title="기본 정보">
        <KV label="회사 ID" value={item["회사 ID"]} />
        <KV label="회사명" value={item["회사명"]} />
        <KV label="담당자" value={item["담당자"]} />
        <KV label="이메일" value={item["이메일"]} />
        <KV label="연락처" value={item["연락처"]} />
        <KV label="유입월" value={item["유입월"]} />
        <KV label="가입일" value={item["가입일"]} />
        <KV label="마케팅수신동의" value={item["마케팅수신동의"]} />
        <KV label="테스트 여부" value={item["테스트 여부"]} />
        <KV label="시트" value={item["_sheet"]} />
        <KV label="행번호" value={item["_row"]} />
        <KV label="ID" value={<Code>{item["_id"]}</Code>} />
      </Section>

      {/* 컨택 & 종료 */}
      <Section title="컨택 & 종료">
        <KV label="1차 컨택" value={item["1차 컨택"]} />
        <KV label="2차 컨택" value={item["2차 컨택"]} />
        <KV label="3차 컨택 (종료일)" value={item["3차 컨택 (종료일)"]} />
        <KV label="종료일" value={item["종료일"]} />
      </Section>

      {/* D7 / M1 */}
      <Section title="D7 / M1 지표">
        <KV label="D7_1" value={item["D7_1"] ?? item["d7_1"]} />
        <KV label="M1_1" value={item["M1_1"] ?? item["m1_1"]} />
        <KV label="D7_2" value={item["D7_2"] ?? item["d7_2"]} />
        <KV label="M1_2" value={item["M1_2"] ?? item["m1_2"]} />
        <KV label="8/28" value={item["8/28"] ?? item["snapshot"]} />
      </Section>

      {/* 상담/후속 */}
      <Section title="상담 / 후속">
        <KV label="상담내용" value={item["상담내용"]} />
        <KV label="후속조치" value={item["후속조치"]} />
      </Section>
    </VStack>
  );
}

// --- 작은 서브 컴포넌트들 ---------------------------------------
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Box>
      <Heading size="sm" mb={2}>
        {title}
      </Heading>
      <Table.Root size="sm" variant="outline">
        <Table.Body>{children}</Table.Body>
      </Table.Root>
    </Box>
  );
}

function KV({ label, value }: { label: string; value: any }) {
  return (
    <Table.Row>
      <Table.Cell width="200px" fontWeight="semibold" bg="gray.50">
        {label}
      </Table.Cell>
      <Table.Cell>{value || <Text color="gray.400">-</Text>}</Table.Cell>
    </Table.Row>
  );
}