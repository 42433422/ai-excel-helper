import { ref, computed, onUnmounted } from 'vue';
import { useJarvisChatStore } from '@/stores/jarvisChat';

type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onstart: (() => void) | null;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

export function useJarvisChat(): any {
  const store = useJarvisChatStore();

  const isListening = ref(false);
  const recognition = ref<SpeechRecognitionLike | null>(null);

  const messages = computed(() => store.messages);
  const isRecording = computed(() => store.isRecording);
  const isPlaying = computed(() => store.isPlaying);
  const statusText = computed(() => store.statusText);
  const isCoreSpeaking = computed(() => store.isCoreSpeaking);

  const sendMessage = async (message: string) => {
    return await store.sendMessage(message);
  };

  const addMessage = (content: string, type: 'user' | 'ai' | 'task' = 'ai') => {
    store.addMessage(content, type);
  };

  const addTaskMessage = (content: string, taskData: any) => {
    store.addTaskMessage(content, taskData);
  };

  const startRecording = () => {
    const hasSpeech = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    if (!hasSpeech) {
      console.warn('Speech recognition not supported');
      return;
    }

    const SpeechRecognitionCtor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    recognition.value = new SpeechRecognitionCtor() as SpeechRecognitionLike;
    recognition.value.lang = 'zh-CN';
    recognition.value.continuous = false;
    recognition.value.interimResults = false;

    recognition.value.onstart = () => {
      isListening.value = true;
      store.startRecording();
    };

    recognition.value.onresult = (event: any) => {
      const transcript = event?.results?.[0]?.[0]?.transcript || '';
      store.stopRecording();
      if (transcript) {
        void sendMessage(transcript);
      }
    };

    recognition.value.onerror = (event: any) => {
      console.error('Speech recognition error:', event?.error);
      store.stopRecording();
      isListening.value = false;
    };

    recognition.value.onend = () => {
      isListening.value = false;
      if (store.isRecording) {
        store.stopRecording();
      }
    };

    recognition.value.start();
  };

  const stopRecording = () => {
    if (recognition.value) {
      recognition.value.stop();
      recognition.value = null;
    }
    isListening.value = false;
    store.stopRecording();
  };

  const queueVoice = (text: string) => {
    store.queueVoice(text);
  };

  const speak = (text: string) => {
    store.queueVoice(text);
  };

  const setStatus = (text: string) => {
    store.setStatus(text);
  };

  const setCoreSpeaking = (speaking: boolean) => {
    store.setCoreSpeaking(speaking);
  };

  const clearMessages = () => {
    store.clearMessages();
  };

  const clearVoiceQueue = () => {
    store.clearVoiceQueue();
  };

  onUnmounted(() => {
    stopRecording();
  });

  return {
    messages,
    isRecording,
    isPlaying,
    isListening,
    statusText,
    isCoreSpeaking,
    sendMessage,
    addMessage,
    addTaskMessage,
    startRecording,
    stopRecording,
    queueVoice,
    speak,
    setStatus,
    setCoreSpeaking,
    clearMessages,
    clearVoiceQueue
  };
}
