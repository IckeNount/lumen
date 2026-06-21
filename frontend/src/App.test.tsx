import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the research console shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ status: "ok" }))),
    );

    render(<App />);

    expect(screen.getByRole("heading", { name: "Lumen" })).toBeInTheDocument();
    expect(screen.getByLabelText("Question composer")).toBeInTheDocument();
    expect(screen.getByLabelText("Research report")).toBeInTheDocument();
    expect(screen.getByLabelText("Evidence metadata")).toBeInTheDocument();
    expect(await screen.findByText("API online")).toBeInTheDocument();
  });
});
