# Prints dos guias de integração

Cada passo de guia que espera um print procura o arquivo neste caminho:

```
public/assets/integration-guides/<provider>/<slug>.png
```

Enquanto o arquivo não existir, o Bioma mostra um espaço tracejado no lugar
com o caminho exato esperado — tanto na tela quanto no PDF. **Nada quebra sem
os prints**; eles são opcionais e podem ser adicionados aos poucos.

Para adicionar: salve o PNG no caminho indicado pelo placeholder e recarregue
a página. Nenhum código precisa ser alterado.

## Recomendações

- **Formato:** PNG, largura ~1200px.
- **Recorte:** só a área relevante da tela, não o monitor inteiro.
- **Destaque:** se quiser marcar o ponto exato, use um retângulo de contorno
  na cor de destaque da EG — `#3ac97b` (menta).
- **Privacidade:** borre IDs de conta reais, e-mails e nomes de clientes antes
  de salvar. Esses guias são enviados para clientes.

## Slugs esperados por provider

| Provider | Slugs |
|---|---|
| `google_ads` | `service-account-email`, `customer-id`, `conceder-acesso` |
| `ga4` | `service-account-email`, `property-id`, `acesso-ga4` |
| `search_console` | `service-account-email`, `propriedade`, `acesso-gsc` |
| `gtm` | `service-account-email`, `container-id`, `acesso-gtm` |
| `meta_ads` | `solicitar-acesso`, `ad-account-id` |
| `linkedin_ads` | `account-id`, `acesso-linkedin` |
| `instagram_organic` | `conta-business`, `ig-account-id`, `permissoes-ig` |
| `google_business_profile` | `solicitar-api`, `service-account-email`, `acesso-gbp`, `location-id` |
| `google_adsense` | `service-account-email`, `publisher-id`, `acesso-adsense` |
| `youtube_organic` | `channel-id` |
| `tiktok_organic` | `consentimento-tiktok`, `conectado` |
| `tiktok_ads` | `selecionar-contas`, `contas-conectadas` |
| `linkedin_organic` | `admin-pagina`, `consentimento-linkedin`, `paginas-conectadas` |
| `rd_station_crm` | `token-rd` |
| `hubspot` | `criar-app-privado`, `escopos`, `token-hubspot` |

A lista canônica está em `bioma/apps/web/src/lib/integration-guides.ts` — o
campo `screenshot` de cada passo é o slug. Para adicionar um slot novo, basta
incluir `screenshot: "novo-slug"` no passo desejado.
