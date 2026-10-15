import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Header } from "./Header";

describe("Header identity", () => {
  it("does not present demo ops credentials as a logged-in user", () => {
    render(<Header title="Weather Intelligence" />);
    expect(screen.queryByText("Ops Coordinator")).toBeNull();
    expect(screen.queryByText("demo@visionguard.local")).toBeNull();
    expect(screen.getByText("Decision-support console")).toBeTruthy();
    expect(screen.getByText(/No user login/)).toBeTruthy();
  });
});
