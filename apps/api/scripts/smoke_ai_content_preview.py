"""Smoke dos geradores de PRÉVIA de conteúdo (sem OPENAI_API_KEY).

Chama `bioma_worker.ai_content.generate_content` direto, sem HTTP: garante que
sem chave o Bioma devolve prévia rotulada (`generation_mode == "preview"`) com a
forma certa, em vez de estourar ou inventar resultado de IA.

Chamava-se `smoke_ai_content` e colidia com o smoke de mesmo nome em
`apps/worker/scripts/` — o runner indexa SKIP/MUTABLE/NEEDS_API_ENV por nome de
arquivo, então uma decisão sobre um valeria calada para o outro.
"""

import sys
from pathlib import Path

# Add apps/worker to sys.path
worker_path = Path(__file__).resolve().parent.parent.parent / "worker"
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from types import SimpleNamespace
from bioma_worker.ai_content import generate_content

def main():
    print("Testing bioma_worker multimodal content generation...")
    settings = SimpleNamespace(openai_api_key=None)

    # 1. Test social_posts
    req_posts = {
        "content_type": "social_posts",
        "brief": "Lançamento da nova metodologia EverGreen para empresas B2B.",
        "channels": ["instagram", "linkedin"],
        "quantity": 2,
        "tone": "estratégico e profissional",
        "objective": "gerar reuniões de diagnóstico comercial",
    }
    res_posts = generate_content(req_posts, settings)
    assert res_posts["generation_mode"] == "preview"
    assert len(res_posts["output"]["posts"]) == 2
    assert res_posts["output"]["posts"][0]["channel"] == "instagram"
    print("[OK] social_posts preview generator OK")

    # 2. Test image_generation
    req_images = {
        "content_type": "image_generation",
        "brief": "Criação de artes visuais premium para campanha de anúncios.",
        "channels": ["instagram", "linkedin"],
        "quantity": 2,
        "tone": "moderno e limpo",
        "image_provider": "dalle_3",
        "objective": "anúncios de meio de funil",
    }
    res_images = generate_content(req_images, settings)
    assert res_images["generation_mode"] == "preview"
    assert len(res_images["output"]["images"]) == 2
    assert res_images["output"]["images"][0]["provider"] == "dalle_3"
    assert "prompt_en" in res_images["output"]["images"][0]
    print("[OK] image_generation preview generator OK")

    # 3. Test video_scripts
    req_videos = {
        "content_type": "video_scripts",
        "brief": "Roteiro de anúncio em vídeo para Reels/TikTok sobre Raio-X Comercial.",
        "channels": ["instagram", "tiktok"],
        "quantity": 2,
        "tone": "dinâmico e persuasivo",
        "objective": "conversão direta no formulário",
    }
    res_videos = generate_content(req_videos, settings)
    assert res_videos["generation_mode"] == "preview"
    assert len(res_videos["output"]["video_scripts"]) == 2
    assert "hook_0_3s" in res_videos["output"]["video_scripts"][0]
    assert "broll_notes" in res_videos["output"]["video_scripts"][0]
    print("[OK] video_scripts preview generator OK")

    print("\nMULTIMODAL AI CONTENT SMOKE TEST OK!")

if __name__ == "__main__":
    main()
