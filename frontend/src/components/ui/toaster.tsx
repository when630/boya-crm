"use client";

import {
  createToaster,
  Toaster as ChakraToaster,
  Toast,          // 토스트 UI 슬롯들
} from "@chakra-ui/react";

export const toaster = createToaster({
  placement: "top-end",
  // max: 3,
  // overlap: true,
  // gap: "8px",
});

export function Toaster() {
  return (
    <ChakraToaster toaster={toaster}>
      {(toast) => (
        <Toast.Root>
          <Toast.Title>{toast.title}</Toast.Title>
          {toast.description ? (
            <Toast.Description>{toast.description}</Toast.Description>
          ) : null}
          <Toast.CloseTrigger />
        </Toast.Root>
      )}
    </ChakraToaster>
  );
}