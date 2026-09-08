const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
let csrfToken = null;
let sessionRequest;

export async function api(path, body) {
  if (path === "/auth/me" && body === undefined) {
    sessionRequest ||= request(path).finally(() => {
      sessionRequest = null;
    });
    return sessionRequest;
  }
  if (body !== undefined && !csrfToken) {
    await api("/auth/me");
  }
  return request(path, body);
}

async function request(path, body) {
  let response;
  try {
    response = await fetch(`${base}/api${path}`, {
      method: body === undefined ? "GET" : "POST",
      credentials: "include",
      headers:
        body === undefined
          ? {}
          : {
              "Content-Type": "application/json",
              "X-CSRF-Token": csrfToken || "",
            },
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  } catch (error) {
    console.error("API request failed:", error);
    throw new Error(
      "Cannot reach TradeQuest. Check your connection and that the API server is running, then try again.",
    );
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail
          .map(
            (item) => `${item.loc?.slice(1).join(".") || "Input"}: ${item.msg}`,
          )
          .join("; ")
      : data.detail;
    if (response.status === 403 && detail === "Invalid or expired CSRF token; reload your session") {
      csrfToken = null;
      const session = await api("/auth/me");
      if (!session.user) window.dispatchEvent(new Event("session-expired"));
      // Never replay a mutation automatically, especially a trade or reward.
      throw new Error("Your session was refreshed. Sign in if needed, then submit again.");
    }
    if (response.status === 401 && (body === undefined || detail === "Sign in to continue")) {
      csrfToken = null;
      window.dispatchEvent(new Event("session-expired"));
    }
    throw new Error(
      detail || `Request failed (${response.status}). Please try again.`,
    );
  }
  if (data.csrf_token) csrfToken = data.csrf_token;
  if (["/auth/logout", "/auth/reset-password", "/me/delete"].includes(path))
    csrfToken = null;
  return data;
}
