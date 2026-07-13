import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "@/App";

describe("App", () => {
  it("renders the application shell", () => {
    render(<App />);
    expect(screen.getByText("RAG-enterprise")).toBeInTheDocument();
    expect(screen.getByText("Frontend skeleton ready")).toBeInTheDocument();
  });
});
