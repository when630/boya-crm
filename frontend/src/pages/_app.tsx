// src/pages/_app.tsx
import type { AppProps } from "next/app";
import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { Toaster } from "@/components/ui/toaster"; // ✅ 여기서 가져오기

export default function MyApp({ Component, pageProps }: AppProps) {
  return (
    <ChakraProvider value={defaultSystem}>
      <Toaster /> {/* props 없이 OK (우리가 래퍼에서 toaster 바인딩) */}
      <Component {...pageProps} />
    </ChakraProvider>
  );
}