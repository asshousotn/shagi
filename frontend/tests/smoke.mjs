const API = process.env.API_BASE || "http://127.0.0.1:8000/api";
const WEB = process.env.WEB_BASE || "http://127.0.0.1:5173";

async function get(path, headers = {}) {
  const response = await fetch(API + path, { headers });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

async function post(path, body, headers = {}) {
  const response = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.json();
}

async function main() {
  const health = await get("/health");
  if (!health.ok) throw new Error("health failed");

  const html = await (await fetch(WEB)).text();
  if (!html.includes("Taskills")) throw new Error("site html failed");

  const login = await post("/auth/login", { email: "author@demo.ru", password: "demo123" });
  const auth = { Authorization: `Bearer ${login.access_token}` };

  const instructions = await get("/instructions", auth);
  if (!Array.isArray(instructions.items)) throw new Error("catalog failed");

  const analytics = await get("/me/analytics", auth);
  const notifications = await get("/me/notifications", auth);
  const activity = await get("/me/activity", auth);
  const versions = await get("/instructions/1/versions", auth);

  console.log("health ok");
  console.log("site ok");
  console.log("catalog:", instructions.total);
  console.log("analytics instructions:", analytics.instructions);
  console.log("notifications:", notifications.length);
  console.log("activity:", activity.items.length);
  console.log("versions:", versions.length);
  console.log("smoke passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
