/**
 * CONTRACT-001 — trava de drift entre os tipos escritos à mão em `lib/api.ts`
 * e o OpenAPI real da API.
 *
 * Por que existe: `lib/api.ts` mantém ~1.200 linhas de tipos espelhando os
 * schemas Pydantic. Nada garantia que os dois concordassem — um campo
 * renomeado no backend só aparecia como `undefined` em runtime, na tela.
 *
 * Como funciona: para cada par (tipo local, schema do OpenAPI) este arquivo
 * afirma, em tempo de compilação, que
 *   1. os conjuntos de chaves são idênticos (pega campo somado, removido ou
 *      renomeado no backend — o drift mais comum e mais caro);
 *   2. o tipo local é atribuível ao do contrato (pega mudança de tipo, mas
 *      permite estreitamento deliberado, como `ClientModule[]` sobre
 *      `string[]` ou um enum local sobre `string`).
 *
 * Este arquivo não gera runtime: só falha `tsc`. Ele não é importado por
 * ninguém de propósito — `tsc -b` compila o projeto inteiro e é aí que a
 * verificação acontece.
 *
 * Ao mexer no backend:
 *   1. `python scripts/export_openapi.py` em `apps/api`
 *   2. `npm run types:api` em `apps/web`
 *   3. `npx tsc -b` — o que quebrar aqui é contrato que mudou de verdade.
 *
 * Cobertura atual: os schemas de leitura mais usados pelas telas. Ampliar é
 * acrescentar uma linha em `ContractChecks`; a intenção é migrar `api.ts`
 * para consumir `components["schemas"][...]` direto e então apagar este
 * arquivo.
 */

import type { components } from "./api-schema";
import type {
  ApprovalSummary,
  ArtifactSummary,
  ClientFileSummary,
  ClientSummary,
  CurrentUser,
  DeliverableSummary,
  FinancialRecordSummary,
  LeadSummary,
  SyncRunSummary,
  WorkspaceSummary,
} from "../lib/api";

type Schemas = components["schemas"];

/** Chaves que existem no contrato e faltam no tipo local (ou vice-versa). */
type KeyDiff<Contract, Local> =
  | Exclude<keyof Contract, keyof Local>
  | Exclude<keyof Local, keyof Contract>;

/**
 * `never` quando o par está em dia. Qualquer outra coisa vira erro de
 * compilação com o nome da chave divergente no texto do erro.
 */
type Conforms<Contract, Local> = KeyDiff<Contract, Local> extends never
  ? Local extends Contract
    ? never
    : ["tipo local não é atribuível ao contrato", Contract, Local]
  : ["chaves divergentes", KeyDiff<Contract, Local>];

/**
 * Cada entrada precisa resolver para `never`. Se não resolver, o erro aponta
 * exatamente qual schema e qual chave saíram de sincronia.
 */
type ContractChecks = {
  ApprovalSummary: Conforms<Schemas["ApprovalSummary"], ApprovalSummary>;
  ArtifactSummary: Conforms<Schemas["ArtifactSummary"], ArtifactSummary>;
  ClientFileSummary: Conforms<Schemas["ClientFileSummary"], ClientFileSummary>;
  ClientSummary: Conforms<Schemas["ClientSummary"], ClientSummary>;
  CurrentUser: Conforms<Schemas["CurrentUserResponse"], CurrentUser>;
  DeliverableSummary: Conforms<Schemas["DeliverableSummary"], DeliverableSummary>;
  FinancialRecordSummary: Conforms<Schemas["FinancialRecordSummary"], FinancialRecordSummary>;
  LeadSummary: Conforms<Schemas["LeadSummary"], LeadSummary>;
  SyncRunSummary: Conforms<Schemas["SyncRunSummary"], SyncRunSummary>;
  WorkspaceSummary: Conforms<Schemas["WorkspaceSummary"], WorkspaceSummary>;
};

/**
 * A asserção. `ContractChecks[keyof ContractChecks]` colapsa para `never`
 * somente quando todas as entradas conformam.
 */
type AssertNoDrift<T extends never> = T;
export type ContractIsInSync = AssertNoDrift<ContractChecks[keyof ContractChecks]>;
