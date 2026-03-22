const API_BASE = '';

const defaultHeaders = {
  'Content-Type': 'application/json'
};

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

async function request(url, options = {}) {
  const fullUrl = API_BASE + url;
  const { skipDefaultJsonHeader = false, ...requestOptions } = options;
  const config = {
    ...requestOptions
  };
  const baseHeaders = skipDefaultJsonHeader ? {} : defaultHeaders;
  config.headers = {
    ...baseHeaders,
    ...(requestOptions.headers || {})
  };

  try {
    const response = await fetch(fullUrl, config);
    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      let errorData = null;
      let errorMessage = `请求失败: ${response.status}`;
      
      if (contentType.includes('application/json')) {
        try {
          errorData = await response.json();
          errorMessage = errorData.message || errorMessage;
        } catch (_) {}
      }
      
      throw new ApiError(errorMessage, response.status, errorData);
    }

    if (options.responseType === 'blob') {
      return response;
    }

    if (contentType.includes('application/json')) {
      return await response.json();
    }

    return response;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message || '网络错误', 0, null);
  }
}

export const api = {
  get(url, params = {}, options = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        searchParams.append(key, value);
      }
    });
    const queryString = searchParams.toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return request(fullUrl, {
      method: 'GET',
      ...options
    });
  },

  post(url, data = {}, options = {}) {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'POST',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  put(url, data = {}, options = {}) {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'PUT',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  patch(url, data = {}, options = {}) {
    const isFormData = typeof FormData !== 'undefined' && data instanceof FormData;
    const headers = { ...(options.headers || {}) };
    return request(url, {
      method: 'PATCH',
      body: isFormData ? data : JSON.stringify(data),
      headers,
      skipDefaultJsonHeader: isFormData,
      ...options
    });
  },

  delete(url, data = {}, options = {}) {
    const config = {
      method: 'DELETE',
      ...options
    };
    if (Object.keys(data).length > 0) {
      config.body = JSON.stringify(data);
    }
    return request(url, config);
  },

  download(url, params = {}, options = {}) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        searchParams.append(key, value);
      }
    });
    const queryString = searchParams.toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return request(fullUrl, {
      method: 'GET',
      responseType: 'blob',
      ...options
    });
  }
};

export { API_BASE, ApiError };
export default api;
