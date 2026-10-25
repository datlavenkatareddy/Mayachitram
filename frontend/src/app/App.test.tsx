import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("MayaChitram", () => {
  it("renders the platform and image workspace", () => {
    render(<App />);
    expect(screen.getByText(/Intelligence for/i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /image analysis workspace/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /drop an image here/i })).toBeInTheDocument();
  });
});
