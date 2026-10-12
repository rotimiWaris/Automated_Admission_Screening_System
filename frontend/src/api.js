let csrf = '';
export async function api(path, options = {}) {
  const {query, ...requestOptions} = options;
  const search = query ? `?${new URLSearchParams(query)}` : '';
  const multipart = options.body instanceof FormData;
  let response;
  try {
    response = await fetch(`/api/${path}/${search}`, {
      credentials: 'same-origin', ...requestOptions,
      headers: {...(multipart ? {} : {'Content-Type': 'application/json'}), 'X-CSRFToken': csrf, ...options.headers},
      body: options.body === undefined ? undefined : multipart ? options.body : JSON.stringify(options.body),
    });
  } catch {
    throw new Error('Cannot reach the server. Check that Django is running and try again.');
  }
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && path !== 'login') window.dispatchEvent(new Event('session-expired'));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status}). Refresh and try again.`);
  if (data.csrf) csrf = data.csrf;
  return data;
}
