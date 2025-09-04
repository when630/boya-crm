// src/pages/trials/index.tsx
import { useEffect, useState } from "react";
import { Box, Heading, Separator } from "@chakra-ui/react";
import { useRouter } from "next/router";
import TrialFilters from "@/components/TrialFilters";
import TrialTable from "@/components/TrialTable";
import { fetchTrials } from "@/lib/api";
import type { SortingState } from "@tanstack/react-table";
import { toaster } from "@/components/ui/toaster";

export default function TrialListPage() {
  const [items, setItems] = useState<any[]>([]);
  const [sorting, setSorting] = useState<SortingState>([]);
  const router = useRouter();

  const load = async (p: Record<string, string> = {}) => {
    try {
      const res = await fetchTrials(p);
      setItems(res.items || []);
    } catch (e: any) {
      toaster.create({
        type: "error",
        title: "데이터 로드 실패",
        description: String(e),
      });
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <Box p={6}>
      <Heading size="lg">트라이얼 리스트 (Y/N 병합)</Heading>
      <Box mt={4}>
        <TrialFilters onApply={(p) => load(p)} />
      </Box>
      <Separator my="16px" /> {/* Divider 대체 */}
      <TrialTable
        data={items}
        sorting={sorting}
        setSorting={setSorting}
        onClickRow={(row) => router.push(`/trials/${encodeURIComponent(row._id)}`)}
      />
    </Box>
  );
}