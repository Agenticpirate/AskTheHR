/**
 * Official WhatsApp Cloud API stub.
 *
 * Cloud API access is free. Outbound reminder TEMPLATES are billed by Meta.
 * There is no official free unlimited outbound reminder blast.
 * Unofficial WhatsApp-web scraping (Baileys etc.) is banned here.
 *
 * POST /api/remind
 *   { plan: "free"|"paid", whatsapp: { optedIn, phone, enabled } }
 *
 * Rejects unless plan === "paid" and whatsapp.enabled.
 * Returns 501 { ok:false, reason:"whatsapp_not_configured" } when
 * WHATSAPP_TOKEN or PHONE_ID are missing.
 */

type WhatsAppBody = {
  optedIn?: boolean;
  phone?: string;
  enabled?: boolean;
};

type Body = {
  plan?: string;
  whatsapp?: WhatsAppBody;
};

type Env = {
  WHATSAPP_TOKEN?: string;
  PHONE_ID?: string;
};

type Ctx = {
  request: Request;
  env: Env;
};

const jsonHeaders = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), { status, headers: jsonHeaders });
}

export async function onRequestPost(context: Ctx): Promise<Response> {
  let body: Body;
  try {
    body = (await context.request.json()) as Body;
  } catch {
    return json({ ok: false, reason: "invalid_json" }, 400);
  }

  if (body.plan !== "paid") {
    return json({ ok: false, reason: "paid_plan_required" }, 403);
  }

  const wa = body.whatsapp;
  if (!wa || wa.enabled !== true) {
    return json({ ok: false, reason: "whatsapp_disabled" }, 403);
  }

  const token = context.env.WHATSAPP_TOKEN;
  const phoneId = context.env.PHONE_ID;
  if (!token || !phoneId) {
    return json({ ok: false, reason: "whatsapp_not_configured" }, 501);
  }

  // Official Graph send would go here with an approved template.
  // This stub never scrapes WhatsApp Web and never invents a free blast.
  return json({ ok: true, queued: true });
}

export async function onRequestOptions(): Promise<Response> {
  return new Response(null, {
    status: 204,
    headers: {
      "access-control-allow-methods": "POST, OPTIONS",
      "access-control-allow-headers": "content-type",
      "access-control-max-age": "86400",
    },
  });
}
