import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, money, number } from "./api";
afterEach(() => vi.restoreAllMocks());
describe("API boundary", () => {
  it("preserves server errors and trace IDs", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              message: "Dataset rejected",
              trace_id: "trace-123",
              details: { valid: false },
            },
          }),
          { status: 422 },
        ),
      ),
    );
    await expect(api("/ingestions")).rejects.toMatchObject({
      message: "Dataset rejected",
      traceId: "trace-123",
      details: { valid: false },
    });
  });
  it("handles non-JSON failures without pretending success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("unavailable", { status: 503 })),
    );
    await expect(api("/snapshots")).rejects.toBeInstanceOf(ApiError);
  });
  it("returns deterministic display formats", () => {
    expect(number(1207)).toBe("1,207");
    expect(money(1000)).toBe("$1,000");
  });
});
