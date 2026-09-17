import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";
import { BrowserRouter } from "react-router-dom";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { isSessionError } from "./lib/format";
import { useUiStore } from "./store/uiStore";

// Sessão expirada precisa derrubar o usuário para o login mesmo com dados em
// cache; sem isso a UI congela com dados velhos e as ações falham em silêncio.
function handleSessionError(client: QueryClient, error: unknown): boolean {
  if (error instanceof Error && isSessionError(error)) {
    client.setQueryData(["user"], null);
    client.removeQueries({ predicate: (query) => query.queryKey[0] !== "user" });
    return true;
  }
  return false;
}

const queryClient: QueryClient = new QueryClient({
  // Sem defaultOptions o React Query usa staleTime: 0 e
  // refetchOnWindowFocus: true — ou seja, TODA remontagem de componente e
  // TODO retorno de aba refazia todas as requisições da tela. Era isso que
  // fazia a tela de Tarefas "carregar e carregar" a cada troca de aba.
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      // Voltar para a aba não precisa refazer tudo; os dados de 1 min atrás
      // servem, e mutações já invalidam o que muda de fato.
      refetchOnWindowFocus: false,
      // Ao refazer, mantém o dado anterior na tela em vez de piscar vazio.
      placeholderData: <T,>(previous: T) => previous,
      retry: 1,
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      handleSessionError(queryClient, error);
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      if (handleSessionError(queryClient, error)) return;
      useUiStore.getState().setDataError(error instanceof Error ? error.message : "Não foi possível concluir a ação.");
    },
    onSuccess: () => {
      useUiStore.getState().setDataError("");
    },
  }),
});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
