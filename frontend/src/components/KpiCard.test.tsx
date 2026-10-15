import { render, screen } from "@testing-library/react";
import { KpiCard } from "../components/KpiCard";
import { describe, it, expect } from "vitest";

describe("KpiCard", () => {
  it("renders label and value", () => {
    render(<KpiCard label="Active disasters" value="3" />);
    expect(screen.getByText("Active disasters")).toBeTruthy();
    expect(screen.getByText("3")).toBeTruthy();
  });
});
