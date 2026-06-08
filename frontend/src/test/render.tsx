import { ReactElement } from "react";
import { render, RenderOptions } from "@testing-library/react";

// Render helper for the new Tailwind+Radix UI. Unlike the legacy Mantine tests, no
// provider is required for unit rendering. As shared providers (Radix Tooltip/Toast)
// are introduced in Phase 1, wrap them here so every screen test gets them for free.
export function renderUI(
  ui: ReactElement,
  options?: Omit<RenderOptions, "wrapper">,
) {
  return render(ui, options);
}

export * from "@testing-library/react";
