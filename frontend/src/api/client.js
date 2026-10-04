export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, body) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const message = typeof data.detail === "string" ? data.detail : `Request failed (${response.status})`;
    throw new ApiError(response.status, message);
  }
  return response.status === 204 ? null : response.json();
}

async function orNull(promise) {
  try {
    return await promise;
  } catch (error) {
    if (error.status === 404) return null;
    throw error;
  }
}

export const api = {
  users: () => request("GET", "/users"),
  today: (id) => request("GET", `/users/${id}/today`),
  patterns: (id) => request("GET", `/users/${id}/patterns`),
  recipe: (id) => request("GET", `/users/${id}/recipe`),
  stats: (id) => request("GET", `/users/${id}/stats`),
  days: (id, from, to) => request("GET", `/users/${id}/days?from=${from}&to=${to}`),
  day: (id, date) => orNull(request("GET", `/users/${id}/days/${date}`)),
  saveSurvey: (id, date, answers) => request("PUT", `/users/${id}/surveys/${date}`, answers),
};
