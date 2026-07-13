const request = require("supertest");
const app = require("../app");

describe("GET /api/auth/reset-password (self-served reset page)", () => {
  it("serves the HTML reset form with the token and a matching CSP script nonce", async () => {
    const res = await request(app).get("/api/auth/reset-password?token=abc123def");

    expect(res.status).toBe(200);
    expect(res.headers["content-type"]).toMatch(/text\/html/);
    expect(res.text).toContain("Reset your EVA password");
    // Token is injected into the page so the form can POST it back.
    expect(res.text).toContain("abc123def");

    // Helmet's default CSP blocks inline scripts; the handler must set a nonce
    // on this response AND on the <script> tag, or the form JS won't run.
    const csp = res.headers["content-security-policy"] || "";
    const nonceMatch = csp.match(/script-src 'nonce-([^']+)'/);
    expect(nonceMatch).not.toBeNull();
    expect(res.text).toContain(`nonce="${nonceMatch[1]}"`);
  });

  it("still returns the page (no crash) when the token is missing", async () => {
    const res = await request(app).get("/api/auth/reset-password");
    expect(res.status).toBe(200);
    expect(res.text).toContain("Reset your password");
  });
});
