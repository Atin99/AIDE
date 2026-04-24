export async function onRequest(context) {
  const origin = new URL(context.request.url).origin;
  const timeoutMs = Math.max(1000, Number(context.env.AIDE_PROXY_TIMEOUT_MS || 300000));

  if (context.request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  const backend = String(context.env.AIDE_BACKEND_URL || "").replace(/\/$/, "");
  if (!backend) {
    return new Response(JSON.stringify({ error: "AIDE_BACKEND_URL is not set" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": origin,
      },
    });
  }

  const inUrl = new URL(context.request.url);
  const proxiedPath = inUrl.pathname.replace(/^\/api/, "");
  const target = `${backend}/api${proxiedPath}${inUrl.search}`;

  const headers = new Headers(context.request.headers);
  headers.delete("host");

  const init = {
    method: context.request.method,
    headers,
    redirect: "follow",
  };

  if (!["GET", "HEAD"].includes(context.request.method)) {
    init.body = await context.request.arrayBuffer();
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  init.signal = controller.signal;

  try {
    const upstream = await fetch(target, init);
    const outHeaders = new Headers(upstream.headers);
    outHeaders.set("Access-Control-Allow-Origin", origin);

    return new Response(upstream.body, {
      status: upstream.status,
      headers: outHeaders,
    });
  } catch (error) {
    if (error && error.name === "AbortError") {
      return new Response(JSON.stringify({ error: `Upstream request timed out after ${Math.round(timeoutMs / 1000)} seconds` }), {
        status: 504,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": origin,
        },
      });
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
