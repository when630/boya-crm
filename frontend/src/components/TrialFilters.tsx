import { HStack, Input, Button, Select, createListCollection, Text } from "@chakra-ui/react";
import { useState } from "react";

type Props = { onApply: (p: Record<string, string>) => void };

// 시트 선택
const SHEET_COLLECTION = createListCollection({
  items: [
    { label: "모든 시트", value: "ALL" },
    { label: "트라이얼(Y)", value: "Y" },
    { label: "트라이얼(N)", value: "N" },
  ],
});

// 테스트 여부
const TEST_COLLECTION = createListCollection({
  items: [
    { label: "Y", value: "Y" },
    { label: "N", value: "N" },
  ],
});

// 마케팅수신동의 (시트의 실제 값과 동일하게: 동의/미동의)
const MKT_COLLECTION = createListCollection({
  items: [
    { label: "동의", value: "동의" },
    { label: "미동의", value: "미동의" },
  ],
});

// 메타(구분/요약) 행 보기 모드
const META_COLLECTION = createListCollection({
  items: [
    { label: "데이터만", value: "exclude" }, // 기본(메타 제외)
    { label: "메타만", value: "only" },
    { label: "모두 보기", value: "include" },
  ],
});

export default function TrialFilters({ onApply }: Props) {
  const [q, setQ] = useState("");
  const [sheet, setSheet] = useState<"ALL" | "Y" | "N">("ALL");
  const [isTest, setIsTest] = useState<"" | "Y" | "N">("");
  const [mkt, setMkt] = useState<"" | "동의" | "미동의">("");
  const [meta, setMeta] = useState<"exclude" | "only" | "include">("exclude"); // 🔹 추가

  return (
    <HStack gap={3} wrap="wrap">
      <Input
        placeholder="검색(회사/담당자/이메일/상담내용/후속조치)"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        width="360px"
      />

      {/* 시트 */}
      <Select.Root
        collection={SHEET_COLLECTION}
        value={sheet ? [sheet] : []}
        onValueChange={(e) => setSheet((e.value[0] ?? "ALL") as "ALL" | "Y" | "N")}
        size="sm"
        width="180px"
      >
        <Select.Label>시트</Select.Label>
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="모든 시트" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
            <Select.ClearTrigger
              onClick={(ev) => {
                ev.stopPropagation();
                setSheet("ALL");
              }}
            />
          </Select.IndicatorGroup>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {SHEET_COLLECTION.items.map((opt) => (
              <Select.Item key={opt.value} item={opt}>
                {opt.label}
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>

      {/* 테스트 여부 */}
      <Select.Root
        collection={TEST_COLLECTION}
        value={isTest ? [isTest] : []}
        onValueChange={(e) => setIsTest((e.value[0] ?? "") as "" | "Y" | "N")}
        size="sm"
        width="140px"
      >
        <Select.Label>테스트 여부</Select.Label>
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="테스트 여부" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
            <Select.ClearTrigger
              onClick={(ev) => {
                ev.stopPropagation();
                setIsTest("");
              }}
            />
          </Select.IndicatorGroup>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {TEST_COLLECTION.items.map((opt) => (
              <Select.Item key={opt.value} item={opt}>
                {opt.label}
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>

      {/* 마케팅수신동의 (값을 동의/미동의로 맞춤) */}
      <Select.Root
        collection={MKT_COLLECTION}
        value={mkt ? [mkt] : []}
        onValueChange={(e) => setMkt((e.value[0] ?? "") as "" | "동의" | "미동의")}
        size="sm"
        width="160px"
      >
        <Select.Label>마케팅수신동의</Select.Label>
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="마케팅수신동의" />
          </Select.Trigger>
          <Select.IndicatorGroup>
            <Select.Indicator />
            <Select.ClearTrigger
              onClick={(ev) => {
                ev.stopPropagation();
                setMkt("");
              }}
            />
          </Select.IndicatorGroup>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {MKT_COLLECTION.items.map((opt) => (
              <Select.Item key={opt.value} item={opt}>
                {opt.label}
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>

      {/* 🔹 메타 행 보기 모드 */}
      <Select.Root
        collection={META_COLLECTION}
        value={[meta]}
        onValueChange={(e) => setMeta((e.value[0] ?? "exclude") as "exclude" | "only" | "include")}
        size="sm"
        width="140px"
      >
        <Select.Label>행 타입</Select.Label>
        <Select.Control>
          <Select.Trigger>
            <Select.ValueText placeholder="행 타입" />
          </Select.Trigger>
        </Select.Control>
        <Select.Positioner>
          <Select.Content>
            {META_COLLECTION.items.map((opt) => (
              <Select.Item key={opt.value} item={opt}>
                {opt.label}
              </Select.Item>
            ))}
          </Select.Content>
        </Select.Positioner>
      </Select.Root>

      <Button
        colorScheme="blue"
        onClick={() =>
          onApply({
            q,
            sheet,
            meta, // 🔹 백엔드로 meta 전달
            ["테스트 여부"]: isTest,
            ["마케팅수신동의"]: mkt,
          })
        }
      >
        적용
      </Button>
    </HStack>
  );
}