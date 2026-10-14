"""Gera datasets mockados e realistas para a Univet Loupes Brasil para montagem do Dashboard no Looker Studio / BigQuery.
Gera 3 arquivos CSV em apps/api/seed_data/looker_mock/:
  1. univet_leads_kommo.csv (Funil de Leads, 12 campos da Bruna, estágios e representantes)
  2. univet_vendas_nomus.csv (Pedidos faturados no Nomus, faturamento real e NFs)
  3. univet_aquisicao_canais.csv (SEO, GEO, Google Ads, Meta Ads, investimento e CAC)
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "seed_data" / "looker_mock"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPRESENTANTES = {
    "SP": "Carlos Eduardo (SP Capital/Interior)",
    "RJ": "Mariana Souza (RJ/ES)",
    "MG": "Roberto Alencar (Minas Gerais)",
    "PR": "Lucas Fagundes (Sul - PR/SC)",
    "RS": "Lucas Fagundes (Sul - RS)",
    "BA": "Fernanda Lima (Nordeste)",
    "GO": "Thiago Mendes (Centro-Oeste)",
}

SEGMENTOS = [
    "Odontologia Clínica", "Cirurgia Bucomaxilofacial", "Implantodontia",
    "Endodontia", "Cirurgia Geral / Plástica", "Oftalmologia", "Veterinária"
]

PRODUTOS = [
    "Lupa Galileu (Quick)", "Lupa Prismática (Ergo/High)", "Lupa TTL Customizada",
    "Iluminação LED EOS", "Kit Lupa Ergo + LED EOS", "Óculos de Proteção Laser"
]

CANAIS = [
    "Google Orgânico (SEO)", "Google AI Overview (GEO)", "Google Ads (Search)",
    "Meta Ads (Instagram)", "Indicação de Colega", "Congresso CIOSP"
]

STATUS_KOMMO = [
    ("Novo Lead", 0.30),
    ("Contato Inicial (Bruna)", 0.25),
    ("Demonstração Agendada", 0.15),
    ("Proposta Enviada", 0.12),
    ("Venda Ganha (Nomus)", 0.10),
    ("Perdido", 0.08)
]

MOTIVOS_PERDA = [
    "Preço/Orçamento elevado", "Comprou da concorrência",
    "Sem interesse imediato", "Região sem representante presencial"
]

def generate_leads():
    random.seed(42)
    leads = []
    base_date = datetime.now() - timedelta(days=60)

    for i in range(1, 151):
        lead_date = base_date + timedelta(days=random.randint(0, 59), hours=random.randint(8, 18))
        uf = random.choice(list(REPRESENTANTES.keys()))
        rep = REPRESENTANTES[uf]
        seg = random.choice(SEGMENTOS)
        prod = random.choice(PRODUTOS)
        origem = random.choice(CANAIS)

        # Escolhe status com pesos
        r = random.random()
        cumulative = 0
        status = "Novo Lead"
        for st, weight in STATUS_KOMMO:
            cumulative += weight
            if r <= cumulative:
                status = st
                break

        preco = 0
        data_fechamento = ""
        motivo_perda = ""
        data_visita = ""

        if status == "Demonstração Agendada":
            data_visita = (lead_date + timedelta(days=random.randint(3, 10))).strftime("%Y-%m-%d")
        elif status == "Proposta Enviada":
            preco = random.choice([5800, 7500, 9200, 12500, 16800])
        elif status == "Venda Ganha (Nomus)":
            preco = random.choice([5800, 7500, 9200, 12500, 16800])
            data_fechamento = (lead_date + timedelta(days=random.randint(7, 25))).strftime("%Y-%m-%d %H:%M:%S")
        elif status == "Perdido":
            motivo_perda = random.choice(MOTIVOS_PERDA)
            data_fechamento = (lead_date + timedelta(days=random.randint(3, 15))).strftime("%Y-%m-%d %H:%M:%S")

        tipo_atendimento = "Venda nova" if random.random() > 0.15 else random.choice(["Garantia", "Reparo", "Peças/Acessórios"])
        solicitacao_inicial = random.choice(["Preço", "Catálogo", "Visita presencial", "Dúvida técnica", "Representante"])

        leads.append({
            "lead_id": 10000 + i,
            "nome_cliente": f"Dr(a). Profissional {i}",
            "data_criacao": lead_date.strftime("%Y-%m-%d %H:%M:%S"),
            "data_fechamento": data_fechamento,
            "status": status,
            "valor_proposta": preco,
            "origem": origem,
            "segmento": seg,
            "produto_interesse": prod,
            "uf": uf,
            "representante": rep,
            "tipo_atendimento": tipo_atendimento,
            "solicitacao_inicial": solicitacao_inicial,
            "data_visita": data_visita,
            "motivo_perda": motivo_perda,
            "instagram": f"@dr_univet_{i}" if random.random() > 0.4 else ""
        })

    # Grava CSV de leads
    path = OUTPUT_DIR / "univet_leads_kommo.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(leads[0].keys()))
        writer.writeheader()
        writer.writerows(leads)
    print(f"[OK] Gerado {path} ({len(leads)} leads)")
    return leads

def generate_vendas_nomus(leads):
    vendas = []
    pedidos_faturados = [l for l in leads if l["status"] == "Venda Ganha (Nomus)"]

    for idx, l in enumerate(pedidos_faturados, 1):
        vendas.append({
            "numero_pedido_nomus": 54000 + idx,
            "lead_id_kommo": l["lead_id"],
            "cliente_nome": l["nome_cliente"],
            "data_faturamento": l["data_fechamento"] or l["data_criacao"],
            "valor_total_faturado": l["valor_proposta"],
            "numero_nfe": 12000 + idx,
            "produto": l["produto_interesse"],
            "segmento": l["segmento"],
            "uf": l["uf"],
            "representante": l["representante"],
            "origem_lead": l["origem"]
        })

    path = OUTPUT_DIR / "univet_vendas_nomus.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(vendas[0].keys()))
        writer.writeheader()
        writer.writerows(vendas)
    print(f"[OK] Gerado {path} ({len(vendas)} vendas faturadas)")

def generate_aquisicao():
    canais_data = [
        {"canal": "Google Orgânico (SEO)", "visitas": 4200, "investimento_reais": 0, "leads_gerados": 38, "vendas_faturadas": 5, "receita_faturada": 47500},
        {"canal": "Google AI Overview (GEO)", "visitas": 1850, "investimento_reais": 0, "leads_gerados": 24, "vendas_faturadas": 4, "receita_faturada": 38000},
        {"canal": "Google Ads (Search)", "visitas": 2900, "investimento_reais": 5400, "leads_gerados": 35, "vendas_faturadas": 3, "receita_faturada": 28500},
        {"canal": "Meta Ads (Instagram)", "visitas": 3600, "investimento_reais": 4200, "leads_gerados": 31, "vendas_faturadas": 2, "receita_faturada": 19000},
        {"canal": "Indicação de Colega", "visitas": 310, "investimento_reais": 0, "leads_gerados": 14, "vendas_faturadas": 2, "receita_faturada": 19000},
        {"canal": "Congresso CIOSP", "visitas": 450, "investimento_reais": 8000, "leads_gerados": 8, "vendas_faturadas": 1, "receita_faturada": 12500},
    ]

    for c in canais_data:
        c["cac_reais"] = round(c["investimento_reais"] / c["vendas_faturadas"], 2) if c["vendas_faturadas"] > 0 else 0
        c["roas"] = round(c["receita_faturada"] / c["investimento_reais"], 2) if c["investimento_reais"] > 0 else "Orgânico (Infinito)"

    path = OUTPUT_DIR / "univet_aquisicao_canais.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(canais_data[0].keys()))
        writer.writeheader()
        writer.writerows(canais_data)
    print(f"[OK] Gerado {path} ({len(canais_data)} canais)")

if __name__ == "__main__":
    leads = generate_leads()
    generate_vendas_nomus(leads)
    generate_aquisicao()
