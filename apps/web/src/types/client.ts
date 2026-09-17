export type ClientStatus = "onboarding" | "ativo" | "pausado" | "churned";

export interface ClientContact {
  name: string;
  role: string;
  email?: string;
}

export interface Client {
  client_id: string;
  company_name: string;
  website?: string;
  niche?: string;
  status: ClientStatus;
  purchased_services: string[];
  oferta?: { nivel?: string };
  main_contacts?: ClientContact[];
  kommo?: { ativo?: boolean };
  engenharia?: { tem_projeto?: boolean };
  datas?: { entrada?: string; renovacao?: string };
  // injected by /api/clients
  _dir: string;
  _is_template: boolean;
}
