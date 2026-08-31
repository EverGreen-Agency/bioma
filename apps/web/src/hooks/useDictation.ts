import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Ditado por voz usando a Web Speech API do navegador.
 *
 * Por que esta e não a Realtime API da OpenAI (que é o que o Codex usa —
 * `/v1/realtime` por WebSocket, modo `transcription`, `gpt-4o-mini-transcribe`,
 * VAD no servidor): a Web Speech API **não consome cota nenhuma**. O
 * reconhecimento acontece fora do Bioma, sem provedor configurado, sem token e
 * sem custo. Para "falar em vez de digitar" isso basta, e funciona mesmo quando
 * nenhuma conta de IA está ligada.
 *
 * O que se perde: só Chrome e Edge (e Safari com prefixo). Firefox não
 * implementa. Quando precisarmos de transcrição confiável em qualquer navegador
 * — ou de transcrever ARQUIVO de áudio, que esta API não faz — o caminho é a
 * Realtime API pelo plano de roteamento, e aí sim consome cota.
 *
 * `interim` é o texto provisório enquanto você fala; `final` é o que o
 * reconhecedor confirmou. Mostrar os dois separados evita a sensação de que o
 * campo está "corrigindo sozinho" o que você acabou de dizer.
 */

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
};

function recognitionConstructor(): (new () => SpeechRecognitionLike) | null {
  const scope = window as unknown as Record<string, unknown>;
  return (scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionLike)
    | null;
}

const ERROR_MESSAGES: Record<string, string> = {
  "not-allowed": "Permissão de microfone negada pelo navegador.",
  "service-not-allowed": "O navegador bloqueou o reconhecimento de voz.",
  "no-speech": "Não ouvi nada. Tente de novo mais perto do microfone.",
  "audio-capture": "Nenhum microfone encontrado.",
  network: "Sem conexão com o serviço de reconhecimento do navegador.",
};

export function useDictation(onFinalText: (text: string) => void) {
  const [isListening, setIsListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  // A callback muda a cada render (fecha sobre o texto atual do campo); guardar
  // numa ref evita reinstalar o reconhecedor no meio de uma fala.
  const callbackRef = useRef(onFinalText);
  callbackRef.current = onFinalText;

  const isSupported = typeof window !== "undefined" && recognitionConstructor() !== null;

  const stop = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
    setInterim("");
  }, []);

  const start = useCallback(() => {
    const Constructor = recognitionConstructor();
    if (!Constructor) {
      setError("Este navegador não tem reconhecimento de voz. Use Chrome ou Edge.");
      return;
    }

    const recognition = new Constructor();
    recognition.lang = "pt-BR";
    // `continuous` mantém ouvindo entre pausas: ditar um parágrafo tem silêncio
    // no meio, e sem isso o reconhecedor encerra na primeira vírgula.
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event: any) => {
      let finalText = "";
      let interimText = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        if (result.isFinal) finalText += result[0].transcript;
        else interimText += result[0].transcript;
      }
      setInterim(interimText);
      if (finalText.trim()) callbackRef.current(finalText.trim());
    };

    recognition.onerror = (event: any) => {
      setError(ERROR_MESSAGES[event.error] ?? `Falha no reconhecimento: ${event.error}`);
      setIsListening(false);
      setInterim("");
    };

    recognition.onend = () => {
      setIsListening(false);
      setInterim("");
    };

    recognitionRef.current = recognition;
    setError(null);
    setInterim("");
    try {
      recognition.start();
      setIsListening(true);
    } catch {
      // `start()` durante uma sessão já ativa levanta; tratar como "já ouvindo".
      setIsListening(true);
    }
  }, []);

  const toggle = useCallback(() => {
    if (isListening) stop();
    else start();
  }, [isListening, start, stop]);

  useEffect(() => () => recognitionRef.current?.abort(), []);

  return { isSupported, isListening, interim, error, start, stop, toggle, clearError: () => setError(null) };
}
