// HTTP client for the Python AI service (ai-services/, FastAPI on port 8001).
// Server-side only: the INTERNAL_API_KEY is sent from the backend and never reaches the browser.
export class AiServiceError extends Error {
  constructor(message) {
    super(message);
    this.name = "AiServiceError";
  }
}

export function createAiClient({ baseUrl = "http://localhost:8001", apiKey = "", timeoutMs = 20000, fetchImpl = fetch } = {}) {
  const root = baseUrl.replace(/\/+$/, "");

  async function call(method, path, body) {
    let res;
    try {
      res = await fetchImpl(root + path, {
        method,
        headers: { "content-type": "application/json", ...(apiKey ? { "x-api-key": apiKey } : {}) },
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch {
      // Fail closed: callers must stop (no order, no payment) when the AI service cannot be reached.
      throw new AiServiceError("AI service unreachable");
    }
    const json = await res.json().catch(() => null);
    return { status: res.status, body: json };
  }

  return {
    health: () => call("GET", "/health"),
    sales: (body) => call("POST", "/agents/sales", body),
    purchase: (body) => call("POST", "/workflow/purchase", body),
    financial: (body) => call("POST", "/agents/financial", body),
  };
}
