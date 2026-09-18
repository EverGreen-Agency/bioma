export interface BrandDna {
  id: string;
  name: string;
  url: string;
  tagline: string;
  vibe: string;
  archetype: string;
  palette: {
    primary: string;
    secondary: string;
    accent: string;
    background: string;
    text: string;
  };
  typography: {
    heading: string;
    body: string;
    accent: string;
  };
  productPhotos: Array<{
    id: string;
    title: string;
    url: string;
    category: string;
  }>;
}

export interface CompetitorData {
  id: string;
  name: string;
  handle: string;
  followers: string;
  engagementRate: string;
  postingFrequency: string;
  winningFormats: string[];
  contentGaps: string[];
  topPost: {
    title: string;
    format: string;
    metric: string;
    summary: string;
  };
}

export interface SeasonalEvent {
  id: string;
  title: string;
  dateRange: string;
  impact: "ALTO" | "MÉDIO" | "CRÍTICO";
  category: "COMERCIAL" | "CULTURAL" | "INDÚSTRIA";
  description: string;
  recommendedAngle: string;
}

export interface GlobalTrend {
  id: string;
  platform: "TikTok" | "Instagram" | "X / Twitter" | "Reddit" | "Google Trends";
  topic: string;
  momentum: "+185% em 48h" | "+320% nesta semana" | "Pico Viral" | "Emergente";
  volume: string;
  insight: string;
  suggestedHook: string;
}

export interface CarouselSlide {
  slideNumber: number;
  headline: string;
  body: string;
  visualPrompt: string;
  assignedPhotoUrl?: string;
  backgroundColor: string;
  textColor: string;
}

export interface PostIdea {
  id: string;
  title: string;
  category: string;
  visualIdea: {
    previewImage: string;
    concept: string;
  };
  writtenIdea: string;
  suggestedCaption: string;
  hashtags: string[];
  productPhotoIds: string[];
  slidesCount: number;
  slides: CarouselSlide[];
  status: "draft" | "rendered" | "scheduled";
  scheduledFor?: string;
}

export interface MalleableClientPreset {
  brand: BrandDna;
  competitors: CompetitorData[];
  seasonality: SeasonalEvent[];
  trends: GlobalTrend[];
  ideas: PostIdea[];
}

export const POPPI_PRESET: MalleableClientPreset = {
  brand: {
    id: "poppi",
    name: "Poppi Soda",
    url: "https://drinkpoppi.com",
    tagline: "Prebiotic Soda for Clean Gut Health",
    vibe: "Neon Pop, Unhinged Summer, Nostalgic Bright, High-Energy Health",
    archetype: "The Jester / The Rebel",
    palette: {
      primary: "#ff2a85",
      secondary: "#d4ff00",
      accent: "#ff6b1a",
      background: "#fffaf0",
      text: "#1c1a16",
    },
    typography: {
      heading: "Druk Wide / Outfit Bold",
      body: "Inter Tight Medium",
      accent: "Doto Mono 900",
    },
    productPhotos: [
      {
        id: "p1",
        title: "Punch Pop Can",
        url: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&auto=format&fit=crop&q=80",
        category: "Punch Pop",
      },
      {
        id: "p2",
        title: "Strawberry Lemon Can",
        url: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=600&auto=format&fit=crop&q=80",
        category: "Strawberry Lemon",
      },
      {
        id: "p3",
        title: "Orange Splash Can",
        url: "https://images.unsplash.com/photo-1556881286-fc6915169721?w=600&auto=format&fit=crop&q=80",
        category: "Orange Splash",
      },
      {
        id: "p4",
        title: "Cherry Cola Can",
        url: "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop&q=80",
        category: "Cherry Cola",
      },
      {
        id: "p5",
        title: "Poppi Ice Bucket Drop",
        url: "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80",
        category: "Lifestyle",
      },
    ],
  },
  competitors: [
    {
      id: "c1",
      name: "Olipop",
      handle: "@drinkolipop",
      followers: "420K",
      engagementRate: "4.8%",
      postingFrequency: "7x / semana",
      winningFormats: ["Nostalgia anos 90", "Comparações Nutricionais", "Taste Test em lojas"],
      contentGaps: ["Pouco foco em festivais e vida noturna", "Poucos carrosséis humorísticos de 'unhinged summer'"],
      topPost: {
        title: "Refrigerante comum vs Olipop na rotina real",
        format: "Carrossel Comparativo",
        metric: "34.2K likes, 890 comentários",
        summary: "Cards divididos com comparações simples de açúcar e pré-bióticos.",
      },
    },
    {
      id: "c2",
      name: "Culture Pop",
      handle: "@culturepopsoda",
      followers: "115K",
      engagementRate: "3.2%",
      postingFrequency: "4x / semana",
      winningFormats: ["Ingredientes de verdade", "Receitas de mocktails"],
      contentGaps: ["Design muito sóbrio, falta o fator pop/viral", "Pouco uso de collabs com celebridades"],
      topPost: {
        title: "Como misturar com gin sem culpa",
        format: "Vídeo curto / Reels",
        metric: "18.1K likes",
        summary: "Mocktails artesanais em taças elegantes.",
      },
    },
  ],
  seasonality: [
    {
      id: "s1",
      title: "Pico de Verão & Festivais ao Ar Livre",
      dateRange: "Junho — Agosto",
      impact: "CRÍTICO",
      category: "COMERCIAL",
      description: "Momento de consumo máximo de bebidas refrescantes. Consumidores buscam alternativas sem ressaca e com poucas calorias.",
      recommendedAngle: "Carrosséis vibrantes tipo 'Seu Match de Sabor do Verão' e kits para cooler de praia.",
    },
    {
      id: "s2",
      title: "Semana do Bem-Estar & Saúde Digestiva",
      dateRange: "Outubro",
      impact: "ALTO",
      category: "CULTURAL",
      description: "Pico de buscas no Google por 'gut health' e 'pré-bióticos' antes das festas de fim de ano.",
      recommendedAngle: "Explicações científicas descomplicadas em 4 lâminas: 'O que 5g de açúcar fazem no seu intestino'.",
    },
  ],
  trends: [
    {
      id: "t1",
      platform: "TikTok",
      topic: "#SodaSwap / Clean Girl Beverage",
      momentum: "+320% nesta semana",
      volume: "42.8M views",
      insight: "Criadores filmando sua geladeira estética trocando refrigerantes tradicionais por latas coloridas e saudáveis.",
      suggestedHook: "A única troca na sua rotina que não parece dieta: 5g de açúcar e sabor surreal.",
    },
    {
      id: "t2",
      platform: "Instagram",
      topic: "Carrosséis 'Dumb Quiz' / Escolha sua Persona",
      momentum: "Pico Viral",
      volume: "1.2M interações",
      insight: "Formatos onde cada lâmina define um signo ou personalidade com base em um sabor específico.",
      suggestedHook: "Arrasta pro lado pra ver qual lata da Poppi representa a sua energia caótica desse fim de semana.",
    },
    {
      id: "t3",
      platform: "Reddit",
      topic: "r/GutHealth: O mito dos refrigerantes zero",
      momentum: "+185% em 48h",
      volume: "1.4K upvotes",
      insight: "Discussões intensas sobre adoçantes artificiais vs vinagre de maçã e fibras prebióticas.",
      suggestedHook: "Por que refrigerante zero ainda te deixa inchado? A resposta em 3 slides.",
    },
  ],
  ideas: [
    {
      id: "idea-1",
      title: "Your Summer Flavor Match",
      category: "Engajamento & Quiz",
      visualIdea: {
        previewImage: "https://images.unsplash.com/photo-1556881286-fc6915169721?w=800&auto=format&fit=crop&q=80",
        concept: "Swipe-through interativo onde cada sabor combina com um arquétipo de férias de verão, finalizando com CTA para comprar o pack.",
      },
      writtenIdea: "Your Summer Flavor Match. A swipe-through flavor personality quiz where each Poppi can matches a different summer archetype, ending with a shop prompt.",
      suggestedCaption: "your summer personality according to your drink choice 🍓✨ are you the punch pop main character or strawberry lemon wellness bestie? comment your flavor match below! link in bio to shop the summer cooler pack #drinkpoppi #prebioticsoda #summerdrop",
      hashtags: ["#drinkpoppi", "#prebioticsoda", "#summeressentials", "#guttok", "#healthysoda"],
      productPhotoIds: ["p1", "p2", "p3", "p4"],
      slidesCount: 4,
      status: "rendered",
      slides: [
        {
          slideNumber: 1,
          headline: "Which Poppi Can is Your Summer Energy?",
          body: "Swipe through to find your gut-healthy seasonal archetype ☀️",
          visualPrompt: "Pop-art bold layout, bright sunshine yellow background, floating ice cubes and Poppi cans.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1556881286-fc6915169721?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#ff2a85",
          textColor: "#ffffff",
        },
        {
          slideNumber: 2,
          headline: "Punch Pop: The Main Character",
          body: "Never misses a pool party, has 47 playlists, drinks zero fake sugar.",
          visualPrompt: "Vibrant split hot-pink and neon lime screen with cold sparkling drops.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#d4ff00",
          textColor: "#1c1a16",
        },
        {
          slideNumber: 3,
          headline: "Strawberry Lemon: The Golden Hour Girlie",
          body: "Always has SPF 50, pilates at 8am, keeps digestion on 100%.",
          visualPrompt: "Warm pastel orange and blush pink with sunflare reflections.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#fffaf0",
          textColor: "#ff2a85",
        },
        {
          slideNumber: 4,
          headline: "Stock Your Cooler Now",
          body: "Find your 12-pack at Target, Whole Foods or direct via link in bio.",
          visualPrompt: "Bold graphic typography poster with all 4 cans in a row.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#ff6b1a",
          textColor: "#ffffff",
        },
      ],
    },
    {
      id: "idea-2",
      title: "Punch Pop Summer Drop",
      category: "Lançamento & Destaque de Produto",
      visualIdea: {
        previewImage: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=800&auto=format&fit=crop&q=80",
        concept: "Card com estética de pôster solar de alta intensidade destacando o Love Island x Poppi Punch Pop como a bebida oficial da temporada.",
      },
      writtenIdea: "Punch Pop Summer Drop. A single sun-soaked statement card spotlighting the Love Island x Poppi Punch Pop as the official drink of your most unhinged summer yet.",
      suggestedCaption: "the collab your summer has been waiting for - poppi x love island is HERE and she is gorgeous. fruit punch flavor, prebiotic gut health, 5g sugar - basically a vacation in a can. shop the Punch Pop now, link in bio #PoppixLoveIsland #PunchPop",
      hashtags: ["#PoppixLoveIsland", "#PunchPop", "#GutHealth", "#SummerSoda"],
      productPhotoIds: ["p1"],
      slidesCount: 1,
      status: "rendered",
      slides: [
        {
          slideNumber: 1,
          headline: "YOUR SUMMER JUST GOT COUPLED UP",
          body: "Limited edition Punch Pop is officially live. Taste like fruit punch, works like gut health.",
          visualPrompt: "Pink and lime color block, hard drop shadow, can in center stage.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#ff2a85",
          textColor: "#d4ff00",
        },
      ],
    },
    {
      id: "idea-3",
      title: "Soda Swap: Nutrition Breakdown",
      category: "Educativo & Conversão",
      visualIdea: {
        previewImage: "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=800&auto=format&fit=crop&q=80",
        concept: "Infográfico em carrossel limpo e chocante: comparação lado a lado de 39g de açúcar (refrigerante tradicional) vs 5g (Poppi).",
      },
      writtenIdea: "Soda Swap: Nutrition Breakdown. Clean side-by-side comparison showing ordinary soda vs Poppi with real gut health fiber.",
      suggestedCaption: "would you rather drink 39g of refined sugar or 5g of natural sweetness + prebiotics? we thought so. the soda swap you won't regret. tap link in bio to build your custom box! 🍋🫧 #SodaSwap #CleanIngredients",
      hashtags: ["#SodaSwap", "#CleanEating", "#GutHealthMatters", "#Poppi"],
      productPhotoIds: ["p4", "p2"],
      slidesCount: 3,
      status: "draft",
      slides: [
        {
          slideNumber: 1,
          headline: "What's really in your afternoon soda?",
          body: "Swipe to see the side-by-side breakdown your gut wants you to know.",
          visualPrompt: "Split comparison screen with crisp clean typography.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1551024709-8f23befc6f87?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#1c1a16",
          textColor: "#ffffff",
        },
        {
          slideNumber: 2,
          headline: "39g Sugar vs 5g Sugar",
          body: "Traditional soda has ~10 sugar cubes. Poppi has real fruit juice + organic apple cider vinegar.",
          visualPrompt: "Clean minimal nutrition graphic.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#fffaf0",
          textColor: "#1c1a16",
        },
        {
          slideNumber: 3,
          headline: "Taste the Upgrade",
          body: "Zero artificial aftertaste. 100% craveable. Try your first pack today.",
          visualPrompt: "Cold condensation macro photography on colorful can.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#ff6b1a",
          textColor: "#ffffff",
        },
      ],
    },
  ],
};

export const UNIVET_PRESET: MalleableClientPreset = {
  brand: {
    id: "univet",
    name: "Univet Loupes",
    url: "https://univetloupes.com",
    tagline: "High-Precision Italian Surgical & Dental Ergonomics",
    vibe: "Surgical Tech, Italian Precision, Ergonomic Authority, Sleek Monochrome",
    archetype: "The Master Craftsman / The Innovator",
    palette: {
      primary: "#0070f3",
      secondary: "#00dfd8",
      accent: "#ff6b1a",
      background: "#f4f6f9",
      text: "#0b1320",
    },
    typography: {
      heading: "Space Grotesk Bold",
      body: "Plus Jakarta Sans",
      accent: "JetBrains Mono",
    },
    productPhotos: [
      {
        id: "u1",
        title: "Univet Ergo TTL Loupes",
        url: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=600&auto=format&fit=crop&q=80",
        category: "Ergo Loupes",
      },
      {
        id: "u2",
        title: "EOS LED Headlight System",
        url: "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&auto=format&fit=crop&q=80",
        category: "Lighting",
      },
      {
        id: "u3",
        title: "Titanium Frame Fit",
        url: "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600&auto=format&fit=crop&q=80",
        category: "Frames",
      },
    ],
  },
  competitors: [
    {
      id: "uc1",
      name: "Zeiss Medical",
      handle: "@zeissmeditec",
      followers: "280K",
      engagementRate: "2.1%",
      postingFrequency: "3x / semana",
      winningFormats: ["Casos Clínicos", "Depoimentos de Cirurgiões", "Whitepapers"],
      contentGaps: ["Design engessado e corporativo", "Pouco apelo a dentistas jovens em início de carreira"],
      topPost: {
        title: "Neurocirurgia com ampliação 4.5x",
        format: "Vídeo Técnico",
        metric: "12.4K views",
        summary: "Vídeo gravado direto pela óptica cirúrgica.",
      },
    },
    {
      id: "uc2",
      name: "Orascoptic",
      handle: "@orascoptic",
      followers: "95K",
      engagementRate: "3.5%",
      postingFrequency: "5x / semana",
      winningFormats: ["Vídeos de postura Ergo", "Comparações de peso de lupas"],
      contentGaps: ["Falta destaque ao design e conforto italiano"],
      topPost: {
        title: "Sua coluna no final do dia com lupa prismática",
        format: "Carrossel Postural",
        metric: "8.9K likes",
        summary: "Comparação de curvatura cervical do dentista.",
      },
    },
  ],
  seasonality: [
    {
      id: "us1",
      title: "CIOSP (Congresso Internacional de Odontologia)",
      dateRange: "Janeiro / Fevereiro",
      impact: "CRÍTICO",
      category: "INDÚSTRIA",
      description: "Maior evento odontológico da América Latina. Momento de decisão de investimento anual dos cirurgiões-dentistas.",
      recommendedAngle: "Carrossel de reserva de test-drive de lupas personalizadas no estande.",
    },
    {
      id: "us2",
      title: "Mês da Saúde Ocupacional & Postura",
      dateRange: "Abril",
      impact: "ALTO",
      category: "CULTURAL",
      description: "Atenção máxima a lesões por esforço repetitivo (LER/DORT) e afastamento profissional de cirurgiões.",
      recommendedAngle: "Carrossel manifesto: 'Por que 68% dos cirurgiões relatam dores cervicais crônicas e como a óptica de refração resolve'.",
    },
  ],
  trends: [
    {
      id: "ut1",
      platform: "Instagram",
      topic: "#ErgonomiaOdonto / POV Cirurgia",
      momentum: "+185% em 48h",
      volume: "850K interações",
      insight: "Dentistas gravando vídeos de antes e depois da postura usando lupas ergonômicas de 45 e 60 graus.",
      suggestedHook: "Você opera olhando para baixo há anos e sua coluna já começou a cobrar o preço.",
    },
    {
      id: "ut2",
      platform: "TikTok",
      topic: "Dental Student Graduation Gifts / Investimentos de Carreira",
      momentum: "Pico Viral",
      volume: "15.4M views",
      insight: "Recém-formados discutindo os primeiros equipamentos que realmente mudam o valor cobrado nas consultas.",
      suggestedHook: "O primeiro equipamento que se paga no primeiro mês de consultório.",
    },
  ],
  ideas: [
    {
      id: "u-idea-1",
      title: "A Física da Postura Perfeita",
      category: "Autoridade Científica",
      visualIdea: {
        previewImage: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=800&auto=format&fit=crop&q=80",
        concept: "Lupa cirúrgica em iluminação rim light com linhas de graduação em cyan destacando o ângulo refrativo de 48 graus.",
      },
      writtenIdea: "A Física da Postura Perfeita. 4 slides desmistificando o declive cervical e a óptica prisma patenteada da Univet.",
      suggestedCaption: "operar sem dor não é luxo, é sobrevivência profissional. a tecnologia ergonômica Univet projeta o campo cirúrgico diretamente na sua retina enquanto sua coluna permanece 100% reta. agende um test-drive exclusivo no seu consultório #UnivetErgo #CirurgiaSemDor #OdontologiaErgonomica",
      hashtags: ["#UnivetErgo", "#CirurgiaSemDor", "#LupasCirurgicas", "#DentistasDoBrasil"],
      productPhotoIds: ["u1", "u2"],
      slidesCount: 4,
      status: "rendered",
      slides: [
        {
          slideNumber: 1,
          headline: "Sua coluna aguenta mais 10 anos de consultório?",
          body: "O segredo dos cirurgiões que chegam aos 60 anos sem nenhuma dor cervical.",
          visualPrompt: "Sleek medical studio, dark navy background with laser alignment grid.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#0b1320",
          textColor: "#00dfd8",
        },
        {
          slideNumber: 2,
          headline: "O ângulo de inclinação zero",
          body: "Enquanto lupas comuns forçam flexão de 40º do pescoço, o prisma Univet faz a refração óptica perfeita com cabeça neutra.",
          visualPrompt: "Ray tracing schematic showing optical prism path.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#f4f6f9",
          textColor: "#0b1320",
        },
        {
          slideNumber: 3,
          headline: "Iluminação EOS HD",
          body: "Luz coaxial sem sombras. Campo de visão iluminado com pureza cromática perfeita para resinas e tecidos delicados.",
          visualPrompt: "Close-up macro of surgical lens and LED projector.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1516549655169-df83a0774514?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#0b1320",
          textColor: "#ffffff",
        },
        {
          slideNumber: 4,
          headline: "Solicite seu Teste Clínico",
          body: "Um consultor técnico Univet vai até a sua clínica para calibração pupilar sob medida.",
          visualPrompt: "Minimal Italian luxury call to action card.",
          assignedPhotoUrl: "https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=600&auto=format&fit=crop&q=80",
          backgroundColor: "#0070f3",
          textColor: "#ffffff",
        },
      ],
    },
  ],
};

export const INITIAL_PRESETS: Record<string, MalleableClientPreset> = {
  poppi: POPPI_PRESET,
  univet: UNIVET_PRESET,
};
