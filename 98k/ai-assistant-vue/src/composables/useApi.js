import { ref, reactive } from 'vue';

export function useApi(apiFn, options = {}) {
  const data = ref(null);
  const error = ref(null);
  const loading = ref(false);
  const { immediate = false, defaultParams = {} } = options;

  const execute = async (params = {}) => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await apiFn({ ...defaultParams, ...params });
      data.value = result;
      return result;
    } catch (err) {
      error.value = err;
      throw err;
    } finally {
      loading.value = false;
    }
  };

  if (immediate) {
    execute();
  }

  return {
    data,
    error,
    loading,
    execute,
    reset: () => {
      data.value = null;
      error.value = null;
      loading.value = false;
    }
  };
}

export function useMutation(apiFn, options = {}) {
  const { onSuccess, onError } = options;
  const loading = ref(false);
  const error = ref(null);

  const mutate = async (data) => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await apiFn(data);
      if (onSuccess) {
        onSuccess(result);
      }
      return result;
    } catch (err) {
      error.value = err;
      if (onError) {
        onError(err);
      }
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    error,
    mutate
  };
}
