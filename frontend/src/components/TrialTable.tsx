import {
  Table,
  HStack,
  Button,
  Text,
  Select,
  createListCollection,
} from "@chakra-ui/react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import type { SortingState } from "@tanstack/react-table";
import type { Dispatch } from "react";
import { useMemo, useState, useEffect } from "react";

type Props = {
  data: any[];
  columns?: ColumnDef<any, any>[];
  sorting: SortingState;
  setSorting: Dispatch<SortingState>;
  onClickRow?: (row: any) => void;
};

const PAGE_SIZE_COLLECTION = createListCollection({
  items: [
    { label: "10개", value: "10" },
    { label: "25개", value: "25" },
    { label: "50개", value: "50" },
    { label: "100개", value: "100" },
  ],
});

export default function TrialTable({
  data,
  columns,
  sorting,
  setSorting,
  onClickRow,
}: Props) {
  
const defaultColumns = useMemo<ColumnDef<any, any>[]>(() => {
  return [
    // { accessorKey: "_id", header: "ID" },
    { accessorKey: "유입월", header: "유입월" },
    { accessorKey: "가입일", header: "가입일" },
    // { accessorKey: "회사 ID", header: "회사 ID" },
    { accessorKey: "회사명", header: "회사명" },
    { accessorKey: "마케팅수신동의", header: "마케팅수신동의" },
    { accessorKey: "연락처", header: "연락처" },
    { accessorKey: "담당자", header: "담당자" },
    { accessorKey: "이메일", header: "이메일" },
    { accessorKey: "테스트 여부", header: "테스트 여부" },
    { accessorKey: "1차 컨택", header: "1차 컨택" },
    { accessorKey: "2차 컨택", header: "2차 컨택" },
    { accessorKey: "3차 컨택 (종료일)", header: "3차 컨택 (종료일)" },

    // 🔹 추가: D7/M1 1차/2차
    { accessorKey: "D7_1", header: "D7(1)" },
    { accessorKey: "M1_1", header: "M1(1)" },
    { accessorKey: "D7_2", header: "D7(2)" },
    { accessorKey: "M1_2", header: "M1(2)" },

    // { accessorKey: "상담내용", header: "상담내용" },
    // { accessorKey: "후속조치", header: "후속조치" },
    { accessorKey: "종료일", header: "종료일" },
    { accessorKey: "_sheet", header: "시트" },
  ];
}, []);

  // 페이지네이션 상태 (완전 제어)
  const [pageSize, setPageSize] = useState(10);
  const [pageIndex, setPageIndex] = useState(0);

  // 데이터가 바뀌면 첫 페이지로 (필터/검색 후 UX 안정)
  useEffect(() => { setPageIndex(0); }, [data]);

  const table = useReactTable({
    data,
    columns: columns ?? defaultColumns,
    state: {
      sorting,
      pagination: { pageIndex, pageSize },
    },
    onSortingChange: (updater) => {
      const next = typeof updater === "function" ? updater(sorting) : updater;
      setSorting(next);
      setPageIndex(0); // 정렬 변경 시 1페이지로
    },
    onPaginationChange: (updater) => {
      const next =
        typeof updater === "function"
          ? updater({ pageIndex, pageSize })
          : updater;
      setPageIndex(next.pageIndex);
      setPageSize(next.pageSize);
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    manualPagination: false, // 클라이언트 자르기
    // autoResetPageIndex: false, // 필요시 주석 해제
  });

  const pageCount = table.getPageCount();

  return (
    <>
      {/* 테이블 */}
      <Table.Root interactive>
        <Table.Header>
          {/* 여러 헤더 그룹 지원 */}
          {table.getHeaderGroups().map((hg) => (
            <Table.Row key={hg.id}>
              {hg.headers.map((header) => (
                <Table.ColumnHeader
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  cursor={header.column.getCanSort() ? "pointer" : "default"}
                  userSelect="none"
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                  {header.column.getIsSorted() === "asc" ? " ↑" : null}
                  {header.column.getIsSorted() === "desc" ? " ↓" : null}
                </Table.ColumnHeader>
              ))}
            </Table.Row>
          ))}
        </Table.Header>

        <Table.Body>
          {table.getRowModel().rows.map((row) => (
            <Table.Row
              key={row.id}
              onClick={() => onClickRow?.(row.original)}
              _hover={{ bg: "gray.50", cursor: onClickRow ? "pointer" : "default" }}
            >
              {row.getVisibleCells().map((cell) => (
                <Table.Cell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </Table.Cell>
              ))}
            </Table.Row>
          ))}
        </Table.Body>
      </Table.Root>

      {/* 페이지네이션 컨트롤 */}
      <HStack mt={4} justify="space-between" wrap="wrap" gap={3}>
        <HStack>
          <Button
            size="sm"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            variant="outline"
          >
            처음
          </Button>
          <Button
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            variant="outline"
          >
            이전
          </Button>
          <Button
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            variant="outline"
          >
            다음
          </Button>
          <Button
            size="sm"
            onClick={() => table.setPageIndex(pageCount - 1)}
            disabled={!table.getCanNextPage()}
            variant="outline"
          >
            마지막
          </Button>

          <Text ml={2} fontSize="sm">
            페이지 <strong>{pageIndex + 1} / {pageCount || 1}</strong>
          </Text>
        </HStack>

        {/* 페이지 사이즈 선택 (완전 제어) */}
        <HStack>
          <Text fontSize="sm">표시 개수</Text>
          <Select.Root
            collection={PAGE_SIZE_COLLECTION}
            value={[String(pageSize)]}
            onValueChange={(e) => {
              const v = parseInt(e.value[0] ?? "25", 10);
              setPageSize(v);      // ✅ 상태만 변경
              setPageIndex(0);     // ✅ 첫 페이지로
            }}
            size="sm"
            width="120px"
          >
            <Select.Control>
              <Select.Trigger>
                <Select.ValueText />
              </Select.Trigger>
            </Select.Control>
            <Select.Positioner>
              <Select.Content>
                {PAGE_SIZE_COLLECTION.items.map((opt) => (
                  <Select.Item key={opt.value} item={opt}>
                    {opt.label}
                  </Select.Item>
                ))}
              </Select.Content>
            </Select.Positioner>
          </Select.Root>
        </HStack>
      </HStack>
    </>
  );
}