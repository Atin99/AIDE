export async function onRequest(context) {
  const origin = new URL(context.request.url).origin;

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

  const upstream = await fetch(target, init);
  const outHeaders = new Headers(upstream.headers);
  outHeaders.set("Access-Control-Allow-Origin", origin);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}
