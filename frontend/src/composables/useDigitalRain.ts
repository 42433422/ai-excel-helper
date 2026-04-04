import { ref, onMounted, onUnmounted, type Ref } from 'vue';

interface UseDigitalRainOptions {
  width?: number;
  height?: number;
  fontSize?: number;
  chars?: string[];
}

export function useDigitalRain(
  canvasRef: Ref<HTMLCanvasElement | null>,
  options: UseDigitalRainOptions = {}
) {
  const ctx = ref<CanvasRenderingContext2D | null>(null);
  const columns = ref<number[]>([]);
  const drops = ref<number[]>([]);
  const fontSize = ref(options.fontSize || 14);
  const chars = ref(options.chars || ['0', '1']);
  const isRunning = ref(false);
  const animationId = ref<number | null>(null);
  const isWorkMode = ref(false);

  const init = () => {
    if (!canvasRef.value) return;

    const canvas = canvasRef.value;
    const context = canvas.getContext('2d');
    if (!context) return;
    ctx.value = context;

    canvas.width = options.width || window.innerWidth;
    canvas.height = options.height || window.innerHeight;

    const columnCount = Math.floor(canvas.width / fontSize.value);
    columns.value = Array(columnCount).fill(1);
    drops.value = Array(columnCount).fill(0);
  };

  const draw = () => {
    if (!ctx.value || !canvasRef.value) return;

    const canvas = canvasRef.value;
    const context = ctx.value;

    context.fillStyle = isWorkMode.value ? 'rgba(255, 0, 0, 0.05)' : 'rgba(0, 0, 0, 0.05)';
    context.fillRect(0, 0, canvas.width, canvas.height);

    context.fillStyle = isWorkMode.value ? '#ff0000' : '#0f0';
    context.font = `${fontSize.value}px monospace`;

    for (let i = 0; i < drops.value.length; i++) {
      const text = chars.value[Math.floor(Math.random() * chars.value.length)];
      const x = i * fontSize.value;
      const y = drops.value[i] * fontSize.value;

      context.fillText(text, x, y);

      if (y > canvas.height && Math.random() > 0.975) {
        drops.value[i] = 0;
      }

      drops.value[i]++;
    }

    animationId.value = requestAnimationFrame(draw);
  };

  const start = () => {
    if (isRunning.value) return;

    init();
    if (!ctx.value) return;

    isRunning.value = true;
    draw();
  };

  const stop = () => {
    isRunning.value = false;
    if (animationId.value) {
      cancelAnimationFrame(animationId.value);
      animationId.value = null;
    }
    if (ctx.value && canvasRef.value) {
      const canvas = canvasRef.value;
      ctx.value.fillStyle = 'rgba(0, 0, 0, 1)';
      ctx.value.fillRect(0, 0, canvas.width, canvas.height);
      ctx.value.clearRect(0, 0, canvas.width, canvas.height);
    }
  };

  const setWorkMode = (enabled: boolean) => {
    isWorkMode.value = enabled;
  };

  const resize = () => {
    if (!canvasRef.value) return;

    const canvas = canvasRef.value;
    canvas.width = options.width || window.innerWidth;
    canvas.height = options.height || window.innerHeight;

    const columnCount = Math.floor(canvas.width / fontSize.value);
    columns.value = Array(columnCount).fill(1);
    drops.value = Array(columnCount).fill(0);
  };

  const clear = () => {
    if (!ctx.value || !canvasRef.value) return;

    const canvas = canvasRef.value;
    const context = ctx.value;

    context.fillStyle = isWorkMode.value ? 'rgba(255, 0, 0, 1)' : 'rgba(0, 0, 0, 1)';
    context.fillRect(0, 0, canvas.width, canvas.height);
  };

  onMounted(() => {
    window.addEventListener('resize', resize);
  });

  onUnmounted(() => {
    stop();
    window.removeEventListener('resize', resize);
  });

  return {
    isRunning,
    start,
    stop,
    setWorkMode,
    resize,
    clear
  };
}
