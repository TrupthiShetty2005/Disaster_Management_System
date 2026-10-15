import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Sidebar } from "../components/Sidebar";

describe("in-app weather navigation", () => {
  it("swaps the main pane to Weather when the sidebar link is clicked", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Sidebar />
        <Routes>
          <Route path="/dashboard" element={<div>DASHBOARD_PANE</div>} />
          <Route path="/weather" element={<div>WEATHER_PANE</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("DASHBOARD_PANE")).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "Weather" }));
    expect(screen.getByText("WEATHER_PANE")).toBeTruthy();
    expect(screen.queryByText("DASHBOARD_PANE")).toBeNull();
  });

  it("renders Weather for a direct /weather URL", () => {
    render(
      <MemoryRouter initialEntries={["/weather"]}>
        <Routes>
          <Route path="/dashboard" element={<div>DASHBOARD_PANE</div>} />
          <Route path="/weather" element={<div>WEATHER_PANE</div>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("WEATHER_PANE")).toBeTruthy();
    expect(screen.queryByText("DASHBOARD_PANE")).toBeNull();
  });
});
