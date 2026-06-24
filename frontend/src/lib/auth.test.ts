import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { login, isAuthenticated, registerUser } from "@/lib/auth";

describe("auth utility", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("authenticates valid credentials", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);

    expect(await login("user", "password")).toBe(true);
    expect(isAuthenticated()).toBe(true);
  });

  it("rejects invalid credentials", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: false } as Response);

    expect(await login("user", "wrong")).toBe(false);
    expect(isAuthenticated()).toBe(false);
  });

  it("registers a new user", async () => {
    vi.mocked(fetch).mockResolvedValue({ ok: true } as Response);

    expect(await registerUser("new-user", "password")).toBe(true);
    expect(isAuthenticated()).toBe(true);
  });
});
