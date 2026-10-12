import {afterEach, expect, it, vi} from 'vitest';
import {api} from './api';
afterEach(() => vi.unstubAllGlobals());

it('lets the browser set the multipart boundary while sending CSRF', async () => {
  const fetch = vi.fn().mockResolvedValueOnce({ok: true, json: async () => ({csrf: 'test-token'})}).mockResolvedValue({ok: true, json: async () => ({})});
  vi.stubGlobal('fetch', fetch);
  await api('session');
  const body = new FormData(); body.append('file', new File(['data'], 'image.png'));
  await api('ocr', {method: 'POST', body});
  const options = fetch.mock.calls[1][1];
  expect(options.body).toBe(body);
  expect(options.headers['Content-Type']).toBeUndefined();
  expect(options.headers['X-CSRFToken']).toBe('test-token');
  await api('screen', {method: 'POST', body: {rule_id: 1}});
  expect(fetch.mock.calls[2][1].body).toBe('{"rule_id":1}');
});

it('notifies the app when a protected request loses authentication', async () => {
  const expired=vi.fn(); window.addEventListener('session-expired',expired);
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:401,json:async()=>({error:'Sign in'})}));
  try {
    await expect(api('rules')).rejects.toThrow('Sign in');
    expect(expired).toHaveBeenCalledTimes(1);
    await expect(api('login',{method:'POST',body:{}})).rejects.toThrow('Sign in');
    expect(expired).toHaveBeenCalledTimes(1);
  } finally {window.removeEventListener('session-expired',expired);}
});
