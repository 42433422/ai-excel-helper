import { ref, onUnmounted, type Ref } from 'vue';

type EasingFn = (t: number) => number;
type FrameCallback = (...args: any[]) => void;

interface AnimationOptions {
  duration?: number;
  easing?: EasingFn;
  onFrame?: FrameCallback;
  onComplete?: () => void;
  startValue?: number;
  property?: string;
  unit?: string;
  delay?: number;
  fillMode?: string;
}

export function useAnimation(elementRef: Ref<HTMLElement | null>, options: AnimationOptions = {}) {
  const isAnimating = ref(false);
  const animationId = ref<number | null>(null);
  const progress = ref(0);

  const startAnimation = () => {
    if (isAnimating.value) return;
    isAnimating.value = true;
    progress.value = 0;

    const startTime = performance.now();
    const duration = options.duration || 1000;
    const easing = options.easing || ((t: number) => t);

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      progress.value = Math.min(elapsed / duration, 1);
      const easedProgress = easing(progress.value);

      if (elementRef.value && options.onFrame) {
        options.onFrame(elementRef.value, easedProgress);
      }

      if (progress.value < 1) {
        animationId.value = requestAnimationFrame(animate);
      } else {
        isAnimating.value = false;
        if (options.onComplete) {
          options.onComplete();
        }
      }
    };

    animationId.value = requestAnimationFrame(animate);
  };

  const stopAnimation = () => {
    if (animationId.value) {
      cancelAnimationFrame(animationId.value);
      animationId.value = null;
    }
    isAnimating.value = false;
  };

  const resetAnimation = () => {
    stopAnimation();
    progress.value = 0;
  };

  const animateTo = (targetValue: number, duration = 1000, easing: EasingFn = (t) => t) => {
    return new Promise<number>((resolve) => {
      const startValue = options.startValue || 0;
      const startTime = performance.now();

      const animate = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const ratio = Math.min(elapsed / duration, 1);
        const easedProgress = easing(ratio);
        const currentValue = startValue + (targetValue - startValue) * easedProgress;

        if (options.onFrame) {
          options.onFrame(currentValue, easedProgress);
        }

        if (ratio < 1) {
          animationId.value = requestAnimationFrame(animate);
        } else {
          isAnimating.value = false;
          resolve(currentValue);
        }
      };

      isAnimating.value = true;
      animationId.value = requestAnimationFrame(animate);
    });
  };

  const animateLoop = (callback: (progress: number) => void, duration = 1000) => {
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const ratio = (elapsed % duration) / duration;

      callback(ratio);
      animationId.value = requestAnimationFrame(animate);
    };

    isAnimating.value = true;
    animationId.value = requestAnimationFrame(animate);
  };

  onUnmounted(() => {
    stopAnimation();
  });

  return {
    isAnimating,
    progress,
    startAnimation,
    stopAnimation,
    resetAnimation,
    animateTo,
    animateLoop
  };
}

export function useCSSAnimation(
  elementRef: Ref<HTMLElement | null>,
  animationName: string,
  options: AnimationOptions = {}
) {
  const isAnimating = ref(false);

  const play = () => {
    if (!elementRef.value) return;

    isAnimating.value = true;
    elementRef.value.style.animation = `${animationName} ${options.duration || 0.3}s ${
      options.easing || 'ease-out'
    } ${options.delay || 0}s ${options.fillMode || 'forwards'}`;

    if (options.onComplete) {
      const duration = (options.duration || 0.3) * 1000 + (options.delay || 0) * 1000;
      setTimeout(() => {
        isAnimating.value = false;
        options.onComplete?.();
      }, duration);
    }
  };

  const pause = () => {
    if (elementRef.value) {
      elementRef.value.style.animationPlayState = 'paused';
    }
  };

  const resume = () => {
    if (elementRef.value) {
      elementRef.value.style.animationPlayState = 'running';
    }
  };

  const reset = () => {
    if (elementRef.value) {
      elementRef.value.style.animation = 'none';
      isAnimating.value = false;
    }
  };

  return {
    isAnimating,
    play,
    pause,
    resume,
    reset
  };
}

export function useTransition(elementRef: Ref<HTMLElement | null>, options: AnimationOptions = {}) {
  const isTransitioning = ref(false);

  const transition = (toValue: number, duration = 300) => {
    if (!elementRef.value || !options.property) return;

    isTransitioning.value = true;

    const property = options.property;
    const startValue = parseFloat((elementRef.value.style as any)[property] || '0');
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const ratio = Math.min(elapsed / duration, 1);
      const easedProgress = options.easing ? options.easing(ratio) : ratio;
      const currentValue = startValue + (toValue - startValue) * easedProgress;

      (elementRef.value!.style as any)[property] = `${currentValue}${options.unit || 'px'}`;

      if (ratio < 1) {
        requestAnimationFrame(animate);
      } else {
        isTransitioning.value = false;
        options.onComplete?.();
      }
    };

    requestAnimationFrame(animate);
  };

  return {
    isTransitioning,
    transition
  };
}

export const easingFunctions = {
  linear: (t: number) => t,
  easeInQuad: (t: number) => t * t,
  easeOutQuad: (t: number) => t * (2 - t),
  easeInOutQuad: (t: number) => (t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t),
  easeInCubic: (t: number) => t * t * t,
  easeOutCubic: (t: number) => (--t) * t * t + 1,
  easeInOutCubic: (t: number) =>
    t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,
  easeInElastic: (t: number) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0
      ? 0
      : t === 1
      ? 1
      : -Math.pow(2, 10 * t - 10) * Math.sin((t * 10 - 10.75) * c4);
  },
  easeOutElastic: (t: number) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0
      ? 0
      : t === 1
      ? 1
      : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  },
  easeOutBounce: (x: number) => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (x < 1 / d1) {
      return n1 * x * x;
    } else if (x < 2 / d1) {
      return n1 * (x - 1.5 / d1) * (x - 1.5 / d1) + 0.75;
    } else if (x < 2.5 / d1) {
      return n1 * (x - 2.25 / d1) * (x - 2.25 / d1) + 0.9375;
    } else {
      return n1 * (x - 2.625 / d1) * (x - 2.625 / d1) + 0.984375;
    }
  }
};
