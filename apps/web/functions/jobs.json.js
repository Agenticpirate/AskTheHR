export async function onRequestGet() {
  const upstream = await fetch(
    "https://raw.githubusercontent.com/Agenticpirate/AskTheHR/main/apps/web/public/jobs.json"
  );
  if (!upstream.ok || !upstream.body) {
    return new Response('{"error":"jobs_unavailable"}', {
      status: 502,
      headers: { "content-type": "application/json; charset=utf-8" },
    });
  }
  return new Response(upstream.body, {
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=300, s-maxage=1800",
    },
  });
}
